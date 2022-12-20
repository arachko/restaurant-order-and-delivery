import os
from datetime import datetime, timedelta
from decimal import Decimal
from typing import Tuple, Any, List, Dict
from uuid import uuid4

from boto3.dynamodb.conditions import Key
from chalice import Response

from chalicelib.base_class_entity import EntityBase
from chalicelib.carts import Cart
from chalicelib.companies import get_company_settings_record
from chalicelib.constants import keys_structure
from chalicelib.constants.constants import UNAUTHORIZED_USER, ORDER_EMAIL_FROM
from chalicelib.constants.status_codes import http200
from chalicelib.constants.substitute_keys import to_db, from_db
from chalicelib.menu_items import MenuItem
from chalicelib.restaurants import Restaurant
from chalicelib.utils import auth as utils_auth, \
    data as utils_data, \
    db as utils_db, \
    app as utils_app, \
    notifications as utils_notifications, \
    exceptions, \
    email_templates
from chalicelib.utils.logger import logger


class PreOrder(EntityBase):
    pk = keys_structure.pre_orders_pk
    sk = keys_structure.pre_orders_sk

    required_immutable_fields_validation = {
        'id_': lambda x: isinstance(x, str),
        'user_id': lambda x: isinstance(x, str) or None,
        'user_phone_number': lambda x: isinstance(x, str),
        'restaurant_id': lambda x: isinstance(x, str),
        'date_created': lambda x: isinstance(x, str)
    }

    required_mutable_fields_validation = {
        'menu_items': lambda x: isinstance(x, dict),
        'amount': lambda x: isinstance(x, Decimal),
        'delivery_address': lambda x: isinstance(x, str),
        'delivery_price': lambda x: isinstance(x, Decimal),
        "archived": lambda x: isinstance(x, bool)
    }

    optional_fields_validation = {
        'user_email': lambda x: isinstance(x, str),
        'comment': lambda x: isinstance(x, str)
    }

    def __init__(self, company_id, id_, user_id, **kwargs):
        EntityBase.__init__(self, company_id, id_)

        self.request_data = kwargs.get('request_data', {})

        self.menu_item_list: List[MenuItem] = []

        self.user_id: str = user_id
        self.user_phone_number: str = kwargs.get('user_phone_number')
        self.user_email: str = kwargs.get('user_email')
        self.restaurant_id: str = kwargs.get('restaurant_id')
        self.menu_items: Dict = kwargs.get('menu_items', {})
        self.delivery_address: str = kwargs.get('delivery_address')
        self.delivery_price: Decimal = kwargs.get('delivery_price')
        self.amount: Decimal = kwargs.get('amount')
        self.date_created: str = datetime.today().isoformat(timespec='seconds')
        self.archived: bool = kwargs.get('archived', False)
        self.comment_: str = kwargs.get('comment_')
        self.record_type = 'pre_order'

    @classmethod
    def init_request_create_pre_order_unauthorized_user(cls, request):
        logger.info("init_request_create_pre_order_unauthorized_user ::: started")
        company_id = utils_auth.get_company_id_by_request(request)
        request_body = utils_data.parse_raw_body(request)
        utils_data.substitute_keys(request_body, to_db)
        return cls(
            company_id=company_id,
            id_=str(uuid4()).split('-')[0],
            user_id=UNAUTHORIZED_USER,
            restaurant_id=request_body['restaurant_id'],
            delivery_address=request_body['delivery_address'],
            menu_items=request_body['menu_items'],
            user_phone_number=request_body['user_phone_number'],
            user_email=request_body.get('user_email'),
            comment_=request_body.get('comment_')
        )

    @classmethod
    @utils_auth.authenticate_class
    def init_request_create_pre_order_authorized_user(cls, request):
        logger.info("init_request_create_pre_order_authorized_user ::: started")
        auth_result = request.auth_result
        user_id = auth_result['user_id']
        company_id = auth_result['company_id']
        cart: Cart = Cart.init_by_user_id(company_id, user_id)
        request_body = utils_data.parse_raw_body(request)
        utils_data.substitute_keys(request_body, to_db)
        return cls(
            company_id=company_id,
            id_=str(uuid4()).split('-')[0],
            user_id=user_id,
            restaurant_id=cart.restaurant_id,
            delivery_address=request_body['delivery_address'],
            menu_items=cart.menu_items,
            user_phone_number=request_body['user_phone_number'],
            user_email=request_body.get('user_email'),
            comment_=request_body.get('comment_')
        )

    @classmethod
    def init_by_db_record(cls, company_id, id_, user_id):
        c = cls(company_id, id_, user_id)
        c.__init__(**c._get_db_item())
        return c

    @utils_app.request_exception_handler
    @utils_app.log_start_finish
    def endpoint_create_pre_order(self):
        for item in self.menu_items.values():
            menu_item: MenuItem = MenuItem.init_get_by_id(self.company_id, item['id'], self.restaurant_id)
            self.menu_item_list.append(menu_item)
            item['details'] = menu_item.to_ui()
        self._create_db_record()
        return Response(status_code=http200, body=self._to_ui())

    def _get_pk_sk(self) -> Tuple[str, str]:
        return self.pk.format(company_id=self.company_id, user_id=self.user_id), self.sk.format(order_id=self.id_)

    def _to_dict(self):
        return {
            'id_': self.id_,
            'ttl_': int((datetime.today() + timedelta(days=1)).timestamp()),
            'user_id': self.user_id,
            'user_phone_number': self.user_phone_number,
            'user_email': self.user_email,
            'restaurant_id': self.restaurant_id,
            'delivery_address': self.delivery_address,
            'delivery_price': self.delivery_price,
            'date_created': self.date_created,
            'menu_items': self.menu_items,
            'amount': self.amount,
            'archived': self.archived,
            "comment_": self.comment_
        }

    def to_dict(self):
        return self._to_dict()

    def _validate_mandatory_fields(self):
        logger.info(f"validate_mandatory_fields ::: started")
        for key, validator_func in {
            **self.required_immutable_fields_validation,
            **self.required_mutable_fields_validation
        }.items():
            if validator_func(self.db_record.get(key)) is False:
                message = f'Validation error occurred while validating the field={key}'
                logger.error(f"validate_mandatory_fields ::: {message}")
                raise exceptions.ValidationException(message)
        logger.info(f"validate_mandatory_fields ::: finished")

    def _calculate_amount(self):
        self.delivery_price = Restaurant.init_get_by_id(
            self.company_id, self.restaurant_id).get_delivery_price(self.delivery_address)
        self.amount = Decimal(
            sum([item['details']['price'] * item['qty'] for item in self.menu_items.values()])
        ) + self.delivery_price.quantize(Decimal('1.00'))

    def _check_items_availability(self):
        # self.menu_item_list = [MenuItem.init_get_by_id(item['id_'], self.restaurant_id) for item in self.menu_items]
        # items_availability = [{item.id_: item.is_available_right_now()} for item in self.menu_item_list]
        if not all([item.is_available_right_now() for item in self.menu_item_list]):
            raise exceptions.SomeItemsAreNotAvailable('Some items currently unavailable, please delete '
                                                      'them from cart and recreate the order')

    def _create_db_record(self):
        self._calculate_amount()
        self._init_db_record()
        self._validate_mandatory_fields()
        self._check_items_availability()
        utils_db.put_db_record(self.db_record)
        logger.info(f"create_pre_order ::: pre_order {self.id_} successfully created")


class Order(EntityBase):
    pk = keys_structure.orders_pk
    sk = keys_structure.orders_sk

    pk_archived = keys_structure.orders_archived_pk
    sk_archived = keys_structure.orders_archived_sk

    pk_gsi_user_orders = keys_structure.gsi_user_orders_pk
    sk_gsi_user_orders = keys_structure.gsi_user_orders_sk

    pk_gsi_by_user_archived = keys_structure.gsi_orders_archived_pk
    sk_gsi_by_user_archived = keys_structure.gsi_orders_archived_sk

    required_immutable_fields_validation = {
        'id_': lambda x: isinstance(x, str),
        'user_id': lambda x: isinstance(x, str),
        'user_phone_number': lambda x: isinstance(x, str),
        'restaurant_id': lambda x: isinstance(x, str),
        'date_created': lambda x: isinstance(x, str),
        'paid': lambda x: isinstance(x, bool)
    }

    required_mutable_fields_validation = {
        'menu_items': lambda x: isinstance(x, dict),
        'amount': lambda x: isinstance(x, Decimal),
        'delivery_address': lambda x: isinstance(x, str),
        'delivery_price': lambda x: isinstance(x, Decimal),
        "date_updated": lambda x: isinstance(x, str),
        "updated_by": lambda x: isinstance(x, str),
        "archived": lambda x: isinstance(x, bool)
    }

    optional_fields_validation = {
        'user_email': lambda x: isinstance(x, str),
        'comment_': lambda x: isinstance(x, str),
        'feedback': lambda x: isinstance(x, str),
        'feedback_rate': lambda x: isinstance(x, Decimal) and 1 <= x <= 5
    }

    def __init__(self, company_id, id_, user_id, **kwargs):
        EntityBase.__init__(self, company_id, id_)

        self.request_data = kwargs.get('request_data', {})
        self.db_record: dict = {}
        self.pre_order: Any[PreOrder, None] = None
        self.menu_item_list: List[MenuItem] = []

        self.user_id: str = user_id or UNAUTHORIZED_USER
        self.user_phone_number: str = kwargs.get('user_phone_number')
        self.user_email: str = kwargs.get('user_email')
        self.restaurant_id: str = kwargs.get('restaurant_id')
        self.menu_items: dict = kwargs.get('menu_items', {})
        self.delivery_address: str = kwargs.get('delivery_address')
        self.delivery_price: str = kwargs.get('delivery_price')
        self.amount: Decimal = Decimal(kwargs.get('amount')).quantize(Decimal('1.00')) if \
            type(kwargs.get('amount')) in [int, float, Decimal] else None
        self.date_created: str = kwargs.get('date_created') or datetime.today().isoformat(timespec='seconds')
        self.comment_: str = kwargs.get('comment_')
        self.paid: bool = kwargs.get('paid', False)
        self.history: list = kwargs.get('history', ['created'])
        self.date_updated: str = kwargs.get('date_updated') or datetime.today().isoformat(timespec='seconds')
        self.updated_by: str = user_id
        self.archived: bool = kwargs.get('archived', False)
        self.feedback: str = kwargs.get('feedback')
        self.feedback_rate: Any[Decimal, None] = kwargs.get('feedback_rate', None)
        self.record_type = 'order'

    @classmethod
    @utils_auth.authenticate_class
    def init_request_get_order(cls, request, order_id, restaurant_id):
        logger.info("init_request_get_order_authorized_user ::: started")
        auth_result = request.auth_result
        return cls(auth_result['company_id'], order_id, auth_result['user_id'], restaurant_id=restaurant_id)

    @classmethod
    def init_create_order(cls, request, company_id, user_id):
        logger.info("init_create_order ::: started")
        request_body = utils_data.parse_raw_body(request)
        id_ = request_body['pre_order_id']
        c = cls(company_id, id_, user_id)
        c._init_by_pre_order()
        return c

    @classmethod
    def init_request_create_order_unauthorized(cls, request):
        logger.info("init_request_create_order_unauthorized_user ::: started")
        return cls.init_create_order(request, user_id=UNAUTHORIZED_USER,
                                     company_id=utils_auth.get_company_id_by_request(request))

    @classmethod
    @utils_auth.authenticate_class
    def init_request_create_order_authorized(cls, request):
        logger.info("init_request_create_order_authorized_user ::: started")
        auth_result = request.auth_result
        return cls.init_create_order(request, user_id=auth_result['user_id'],
                                     company_id=auth_result['company_id'])

    def fill_items_details(self):
        for item in self.menu_items.values():
            item['details'] = MenuItem.init_get_by_id(self.company_id, item['id'], self.restaurant_id).to_ui()

    @utils_app.request_exception_handler
    @utils_app.log_start_finish
    def endpoint_create_order(self):
        self.fill_items_details()
        self._create_db_record()
        if self.user_id != UNAUTHORIZED_USER:
            Cart.init_by_user_id(company_id=self.company_id, user_id=self.user_id).delete_db_record()
        return Response(status_code=http200, body=self._to_ui())

    @utils_app.request_exception_handler
    @utils_app.log_start_finish
    def endpoint_get_by_id(self):
        self.__init__(**self._get_db_item_by_user_gsi())
        self.fill_items_details()
        return Response(status_code=http200, body=self._to_ui())

    def _init_by_pre_order(self):
        self.pre_order = PreOrder.init_by_db_record(self.company_id, self.id_, self.user_id)
        pre_order_dict = self.pre_order.to_dict()
        del pre_order_dict['date_created']
        self.__init__(company_id=self.company_id, pre_order=self.pre_order, **pre_order_dict)

    def _get_pk_sk(self) -> Tuple[str, str]:
        return self.pk.format(company_id=self.company_id, restaurant_id=self.restaurant_id), self.sk.format(user_id=self.user_id, order_id=self.id_)

    def _get_pk_sk_user_gsi(self) -> Tuple[str, str]:
        return self.pk_gsi_user_orders.format(company_id=self.company_id, user_id=self.user_id), \
               self.sk_gsi_user_orders.format(restaurant_id=self.restaurant_id, order_id=self.id_)

    def _get_db_item_by_user_gsi(self):
        pk_gsi_user_orders, sk_gsi_user_orders = self._get_pk_sk_user_gsi()
        orders = utils_db.query_items_paged(
            key_condition_expression=(
                    Key('gsi_user_orders_partkey').eq(pk_gsi_user_orders) &
                    Key('gsi_user_orders_sortkey').eq(sk_gsi_user_orders)
            ),
            index_name='gsi_user_orders'
        )
        if not orders:
            raise exceptions.OrderNotFound(f'Order with ID {self.id_} not found')
        else:
            return orders[0]

    def _to_dict(self):
        return {
            'company_id': self.company_id,
            'id_': self.id_,
            'user_id': self.user_id,
            'user_phone_number': self.user_phone_number,
            'user_email': self.user_email,
            'restaurant_id': self.restaurant_id,
            'delivery_address': self.delivery_address,
            'delivery_price': self.delivery_price,
            'date_created': self.date_created,
            'menu_items': self.menu_items,
            'amount': self.amount,
            'paid': self.paid,
            "history": self.history,
            "date_updated": self.date_updated,
            'updated_by': self.updated_by,
            'archived': self.archived,
            "comment_": self.comment_,
            "feedback": self.feedback
        }

    def _init_db_record(self):
        pk, sk = self._get_pk_sk()
        pk_gsi_user_orders, sk_gsi_user_orders = self._get_pk_sk_user_gsi()
        self.db_record = {
            'partkey': pk,
            'sortkey': sk,
            'gsi_user_orders_partkey': pk_gsi_user_orders,
            'gsi_user_orders_sortkey': sk_gsi_user_orders,
            'record_type': self.record_type,
            'company_id': self.company_id,
            **self._to_dict()
        }
        utils_data.substitute_keys(dict_to_process=self.db_record, base_keys=to_db)

    def _validate_mandatory_fields(self):
        logger.info(f"validate_mandatory_fields ::: started")
        for key, validator_func in {
            **self.required_immutable_fields_validation,
            **self.required_mutable_fields_validation
        }.items():
            if validator_func(self.db_record.get(key)) is False:
                message = f'Validation error occurred while validating the field={key}'
                logger.error(f"validate_mandatory_fields ::: {message}")
                raise exceptions.ValidationException(message)
        logger.info(f"validate_mandatory_fields ::: finished")

    def _check_items_availability(self):
        # self.menu_item_list = [MenuItem.init_get_by_id(item['id'], self.restaurant_id) for item in self.menu_items]
        # items_availability = [{item.id_: item.is_available_right_now()} for item in self.menu_item_list]
        if not all([item.is_available_right_now() for item in self.menu_item_list]):
            raise exceptions.SomeItemsAreNotAvailable('Some items currently unavailable, please delete '
                                                      'them from cart and recreate the order')

    def _create_db_record(self):
        self._init_db_record()
        self._validate_mandatory_fields()
        self._check_items_availability()
        utils_db.put_db_record(self.db_record)
        logger.info(f"create_order ::: order {self.id_} successfully created")

    def _to_ui(self):
        item = self._to_dict()
        item['items'] = [item._to_ui() for item in self.menu_item_list]
        utils_data.substitute_keys(dict_to_process=item, base_keys=from_db)
        return item

    def to_ui(self):
        return self._to_ui()


def get_conditions_user(company_id, user_id):
    return Key('gsi_user_orders_partkey').eq(Order.pk_gsi_user_orders.format(company_id=company_id, user_id=user_id)), \
        'gsi_user_orders'


def get_conditions_rest_manager(company_id, restaurant_id):
    if not restaurant_id:
        raise exceptions.MissingRestaurantId('restaurant_id must be provided in query parameters')
    return Key('partkey').eq(Order.pk.format(company_id=company_id, restaurant_id=restaurant_id)), None


@utils_app.request_exception_handler
@utils_app.log_start_finish
@utils_auth.authenticate
def endpoint_get_orders(request, entity_type=None, entity_id=None):
    auth_result = request.auth_result
    company_id, user_id, user_role = auth_result['company_id'], auth_result['user_id'], auth_result['role']
    match user_role:
        case 'user':
            key_condition_exp, index_name = get_conditions_user(company_id, user_id)
        case 'restaurant_manager':
            # Todo: check if the manager have permissions to the restaurant (by ID list in manager's record)
            key_condition_exp, index_name = get_conditions_rest_manager(company_id, entity_id)
        case 'admin':
            if entity_type == 'user':
                key_condition_exp, index_name = get_conditions_user(company_id, entity_id)
            elif entity_type == 'restaurant':
                key_condition_exp, index_name = get_conditions_rest_manager(company_id, entity_id)
            else:
                logger.exception(f'endpoint_get_orders ::: Wrong entity_type={entity_type} in case of admin user')
                raise Exception('endpoint_get_orders ::: Wrong entity_type in case of admin user')
        case _:
            raise exceptions.AccessDenied(f"You don't have permissions to access this resource")

    db_records = utils_db.query_items_paged(key_condition_expression=key_condition_exp, index_name=index_name)
    return Response(status_code=http200, body=[Order(**record).to_ui() for record in db_records])


@utils_app.log_start_finish
def db_trigger_send_order_notification(record_old: dict, record_new: dict, event_id: str, event_name: str):
    logger.info(f'db_trigger_send_order_notification ::: order_record={record_new}, {event_id=}, {event_name=}')
    if event_name.lower() == 'insert':
        company_id = record_new.get('company_id')
        settings_record: Dict = get_company_settings_record(company_id)
        order_notification_emails: List = [
            settings_record.get('order_notification_emails'),
            record_new.get('user_email'),
            os.environ.get("ALL_ORDERS_EMAIL")
        ]
        subject = f'New order has been received, ' \
                  f'order ID - {record_new.get("id_")}, ' \
                  f'address - {record_new.get("address")}'
        email_body = email_templates.get_new_order_notification_message(record_new)
        utils_notifications.send_email_ses(order_notification_emails, ORDER_EMAIL_FROM, subject, email_body)
