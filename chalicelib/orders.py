from datetime import datetime, timedelta
from decimal import Decimal
from typing import Tuple, Any, List
from uuid import uuid4

from boto3.dynamodb.conditions import Attr, Key
from chalice import Response

from chalicelib.carts import Cart
from chalicelib.constants import keys_structure
from chalicelib.constants.constants import UNAUTHORIZED_USER
from chalicelib.constants.status_codes import http200
from chalicelib.constants.substitute_keys import to_db, from_db
from chalicelib.menu_items import MenuItem
from chalicelib.utils import auth as utils_auth, data as utils_data, exceptions, db as utils_db, app as utils_app
from chalicelib.utils.data import substitute_keys
from chalicelib.utils.exceptions import SomeItemsAreNotAvailable, OrderNotFound
from chalicelib.utils.logger import logger


class PreOrder:
    pk = keys_structure.pre_orders_pk
    sk = keys_structure.pre_orders_sk

    required_immutable_fields_validation = {
        'id_': lambda x: isinstance(x, str),
        'user_id': lambda x: isinstance(x, str) or None,
        'user_phone_number': lambda x: isinstance(x, str),
        'restaurant_id': lambda x: isinstance(x, str),
        'delivery_address': lambda x: isinstance(x, str),
        'date_created': lambda x: isinstance(x, str)
    }

    required_mutable_fields_validation = {
        'item_ids': lambda x: isinstance(x, list),
        'amount': lambda x: isinstance(x, Decimal),
        "archived": lambda x: isinstance(x, bool)
    }

    optional_fields_validation = {
        'user_email': lambda x: isinstance(x, str),
        'comment': lambda x: isinstance(x, str)
    }

    def __init__(self, id_, user_id, **kwargs):
        self.request_data = kwargs.get('request_data', {})

        self.menu_item_list: Any[List[MenuItem], None] = None

        self.id_: str = id_
        self.user_id: str = user_id
        self.user_phone_number: str = kwargs.get('user_phone_number')
        self.user_email: str = kwargs.get('user_email')
        self.restaurant_id: str = kwargs.get('restaurant_id')
        self.delivery_address: str = kwargs.get('delivery_address')
        self.item_ids: list = kwargs.get('item_ids', [])
        self.amount: Decimal = kwargs.get('amount')
        self.date_created: str = datetime.today().isoformat(timespec='seconds')
        self.archived: bool = kwargs.get('archived', False)
        self.comment_: str = kwargs.get('comment_')

    @classmethod
    def init_request_create_pre_order_unauthorized_user(cls, request):
        logger.info("init_request_create_pre_order_unauthorized_user ::: started")
        request_body = utils_data.parse_raw_body(request)
        substitute_keys(request_body, to_db)
        return cls(
            id_=str(uuid4()).split('-')[0],
            user_id=UNAUTHORIZED_USER,
            **request_body
        )

    @classmethod
    def init_by_db_record(cls, pre_order_id, user_id):
        c = cls(pre_order_id, user_id)
        c.__init__(**c._get_db_item())
        return c

    @utils_app.request_exception_handler
    @utils_app.log_start_finish
    def endpoint_create_pre_order_unauthorized_user(self):
        self.menu_item_list = [MenuItem.init_get_by_id(item, self.restaurant_id) for item in self.item_ids]
        self.create_pre_order()
        return Response(status_code=http200, body=self.to_ui())

    def _get_pk_sk(self) -> Tuple[str, str]:
        return self.pk.format(user_id=self.user_id), self.sk.format(order_id=self.id_)

    def _get_db_item(self):
        return utils_db.get_db_item(*self._get_pk_sk())

    def to_dict(self):
        return {
            'id_': self.id_,
            'user_id': self.user_id,
            'user_phone_number': self.user_phone_number,
            'user_email': self.user_email,
            'restaurant_id': self.restaurant_id,
            'delivery_address': self.delivery_address,
            'date_created': self.date_created,
            'item_ids': self.item_ids,
            'amount': self.amount,
            'archived': self.archived,
            "comment_": self.comment_
        }

    def _init_db_record(self):
        pk, sk = self._get_pk_sk()
        self.db_record = {
            'partkey': pk,
            'sortkey': sk,
            'ttl_': int((datetime.today() + timedelta(days=1)).timestamp()),
            **self.to_dict()
        }
        substitute_keys(dict_to_process=self.db_record, base_keys=to_db)

    def validate_mandatory_fields(self):
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

    def calculate_amount(self):
        self.amount = Decimal(sum([item.price for item in self.menu_item_list])).quantize(Decimal('1.00'))

    def check_items_availability(self):
        # self.menu_item_list = [MenuItem.init_get_by_id(item['id_'], self.restaurant_id) for item in self.item_ids]
        # items_availability = [{item.id_: item.is_available_right_now()} for item in self.menu_item_list]
        if not all([item.is_available_right_now() for item in self.menu_item_list]):
            raise SomeItemsAreNotAvailable('Some items currently unavailable, please delete '
                                           'them from cart and recreate the order')

    def create_pre_order(self):
        self.calculate_amount()
        self._init_db_record()
        self.validate_mandatory_fields()
        self.check_items_availability()
        utils_db.put_db_record(self.db_record)
        logger.info(f"create_pre_order ::: pre_order {self.id_} successfully created")

    def to_ui(self):
        pre_order = self.to_dict()
        pre_order['items'] = [item.to_ui() for item in self.menu_item_list]
        substitute_keys(dict_to_process=pre_order, base_keys=from_db)
        return pre_order


class Order:
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
        'delivery_address': lambda x: isinstance(x, str),
        'date_created': lambda x: isinstance(x, str),
        'paid': lambda x: isinstance(x, bool)
    }

    required_mutable_fields_validation = {
        'item_ids': lambda x: isinstance(x, list),
        'amount': lambda x: isinstance(x, Decimal),
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

    def __init__(self, id_, user_id, **kwargs):
        self.request_data = kwargs.get('request_data', {})
        self.db_record: dict = {}
        self.pre_order: Any[PreOrder, None] = None
        self.menu_item_list: Any[List[MenuItem], None] = None

        self.id_: str = id_
        self.user_id: str = user_id or UNAUTHORIZED_USER
        self.user_phone_number: str = kwargs.get('user_phone_number')
        self.user_email: str = kwargs.get('user_email')
        self.restaurant_id: str = kwargs.get('restaurant_id')
        self.delivery_address: str = kwargs.get('delivery_address')
        self.item_ids: list = kwargs.get('item_ids', [])
        self.amount: Decimal = Decimal(kwargs.get('amount')).quantize(Decimal('1.00')) if \
            type(kwargs.get('amount')) in [int, float, Decimal] else None
        self.date_created: str = kwargs.get('date_created') or datetime.today().isoformat(timespec='seconds')
        self.comment_: str = kwargs.get('comment_')
        self.paid: bool = kwargs.get('paid', False)
        self.history: list = kwargs.get('history', ['created'])
        self.date_updated: str = kwargs.get('date_updated') or datetime.today().isoformat(timespec='seconds')
        self.updated_by: str = kwargs.get('updated_by') or user_id
        self.archived: bool = kwargs.get('archived', False)
        self.feedback: str = kwargs.get('feedback')
        self.feedback_rate: Any[Decimal, None] = kwargs.get('feedback_rate', None)

    @classmethod
    def init_request_create_order_unauthorized_user(cls, request):
        logger.info("init_request_create_order_unauthorized_user ::: started")
        user_id = UNAUTHORIZED_USER
        request_body = utils_data.parse_raw_body(request)
        id_ = request_body['pre_order_id']
        c = cls(id_, user_id)
        c.init_by_pre_order()
        return c

    @utils_app.request_exception_handler
    @utils_app.log_start_finish
    def endpoint_create_order_unauthorized_user(self):
        self.menu_item_list = [MenuItem.init_get_by_id(item, self.restaurant_id) for item in self.item_ids]
        self.create_order()
        return Response(status_code=http200, body=self.to_ui())

    @utils_app.request_exception_handler
    @utils_app.log_start_finish
    def endpoint_get_by_id_unauthorized_user(self):
        self.__init__(**self._get_db_item_by_user_gsi())
        self.menu_item_list = [MenuItem.init_get_by_id(item, self.restaurant_id) for item in self.item_ids]
        return Response(status_code=http200, body=self.to_ui())

    def init_by_pre_order(self):
        self.pre_order = PreOrder.init_by_db_record(self.id_, self.user_id)
        pre_order_dict = self.pre_order.to_dict()
        del pre_order_dict['date_created']
        self.__init__(pre_order=self.pre_order, **pre_order_dict)

    def _get_pk_sk(self) -> Tuple[str, str]:
        return self.pk.format(restaurant_id=self.restaurant_id), self.sk.format(user_id=self.user_id, order_id=self.id_)

    def _get_pk_sk_user_gsi(self) -> Tuple[str, str]:
        return self.pk_gsi_user_orders.format(user_id=self.user_id), \
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
            raise OrderNotFound(f'Order with ID {self.id_} not found')
        else:
            return orders[0]

    def to_dict(self):
        return {
            'id_': self.id_,
            'user_id': self.user_id,
            'user_phone_number': self.user_phone_number,
            'user_email': self.user_email,
            'restaurant_id': self.restaurant_id,
            'delivery_address': self.delivery_address,
            'date_created': self.date_created,
            'item_ids': self.item_ids,
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
            **self.to_dict()
        }
        substitute_keys(dict_to_process=self.db_record, base_keys=to_db)

    def validate_mandatory_fields(self):
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

    def check_items_availability(self):
        # self.menu_item_list = [MenuItem.init_get_by_id(item['id_'], self.restaurant_id) for item in self.item_ids]
        # items_availability = [{item.id_: item.is_available_right_now()} for item in self.menu_item_list]
        if not all([item.is_available_right_now() for item in self.menu_item_list]):
            raise SomeItemsAreNotAvailable('Some items currently unavailable, please delete '
                                           'them from cart and recreate the order')

    def create_order(self):
        self._init_db_record()
        self.validate_mandatory_fields()
        self.check_items_availability()
        utils_db.put_db_record(self.db_record)
        logger.info(f"create_order ::: order {self.id_} successfully created")

    def to_ui(self):
        order = self.to_dict()
        order['items'] = [item.to_ui() for item in self.menu_item_list]
        substitute_keys(dict_to_process=order, base_keys=from_db)
        return order

