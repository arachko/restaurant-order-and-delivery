from datetime import datetime
from decimal import Decimal
from typing import Tuple, List, Dict
from uuid import uuid4

from boto3.dynamodb.conditions import Attr, Key
from chalice import Response

from chalicelib.constants import keys_structure
from chalicelib.constants.status_codes import http200
from chalicelib.constants.substitute_keys import to_db, from_db
from chalicelib.utils import auth as utils_auth, data as utils_data, exceptions, db as utils_db, app as utils_app
from chalicelib.utils.data import substitute_keys
from chalicelib.utils.exceptions import WrongDeliveryAddress
from chalicelib.utils.logger import logger


class Restaurant:
    pk = keys_structure.restaurants_pk
    sk = keys_structure.restaurants_sk

    required_immutable_fields_validation = {
        'id_': lambda x: isinstance(x, str),
        'created_by': lambda x: isinstance(x, str),
        "date_created": lambda x: isinstance(x, str)
    }

    required_mutable_fields_validation = {
        'title': lambda x: isinstance(x, str),
        'address': lambda x: isinstance(x, str),
        'description': lambda x: isinstance(x, str),
        'cuisine': lambda x: isinstance(x, List),
        'opening_time': lambda x: isinstance(x, Decimal),
        'closing_time': lambda x: isinstance(x, Decimal),
        'settings': lambda x: isinstance(x, dict),
        'status_': lambda x: isinstance(x, str),
        "date_updated": lambda x: isinstance(x, str),
        "updated_by": lambda x: isinstance(x, str),
        "archived": lambda x: isinstance(x, bool)
    }

    def __init__(self, id_, **kwargs):
        self.request_data = kwargs.get('request_data', {})
        self.db_record: dict = {}

        self.id_: str = id_
        self.title: str = kwargs.get('title')
        self.address: str = kwargs.get('address')
        self.description: str = kwargs.get('description')
        self.cuisine: list = kwargs.get('cuisine', [])
        self.opening_time: Decimal = Decimal(kwargs.get('opening_time')).quantize(Decimal('1')) if \
            type(kwargs.get('opening_time')) is int else None
        self.closing_time: Decimal = Decimal(kwargs.get('closing_time')).quantize(Decimal('1')) if \
            type(kwargs.get('closing_time')) is int else None
        self.settings: dict = kwargs.get('settings', {})
        self.status_: str = kwargs.get('status') or 'new'
        self.created_by: str = kwargs.get('created_by') or self.request_data.get('auth_result', {}).get('user_id')
        self.updated_by: str = kwargs.get('updated_by') or self.request_data.get('auth_result', {}).get('user_id')
        self.date_created: str = kwargs.get('date_created') or datetime.now().isoformat(timespec="seconds")
        self.date_updated: str = kwargs.get('date_updated') or datetime.now().isoformat(timespec="seconds")
        self.archived: bool = kwargs.get('archived', False)

    @classmethod
    @utils_auth.authenticate_class
    def init_request_create_update(cls, request, restaurant_id=None, special_body=None):
        logger.info("init_request_create_update ::: started")
        request_body = special_body or utils_data.parse_raw_body(request)
        id_ = restaurant_id or str(uuid4())
        return cls(id_=id_, request_data=request.to_dict(), **request_body)

    @classmethod
    def init_get_by_id(cls, restaurant_id):
        logger.info("init_request_get_by_id ::: started")
        c = cls(restaurant_id)
        c.__init__(**c._get_restaurant_db_item())
        return c

    @classmethod
    def init_request_get_by_id(cls, request, restaurant_id):
        logger.info("init_request_get_by_id ::: started")
        c = cls(restaurant_id)
        c.__init__(**c._get_restaurant_db_item())
        return c

    @staticmethod
    @utils_app.log_start_finish
    def endpoint_get_restaurants(request) -> Response:
        filter_expression = Attr('archived').eq(False)
        restaurant_db_records: List[Dict] = utils_db.query_items_paged(
            Key('partkey').eq(keys_structure.restaurants_pk),
            filter_expression=filter_expression
        )
        restaurants: List[Dict] = [Restaurant(**record).to_ui() for record in restaurant_db_records]
        logger.info(f"endpoint_get_restaurants ::: returning restaurants={[rest['id'] for rest in restaurants]}")
        return Response(status_code=http200, body=restaurants)

    @utils_app.request_exception_handler
    @utils_app.log_start_finish
    def endpoint_get_restaurant_by_id(self) -> Response:
        restaurant = self.to_ui()
        logger.info(f"endpoint_get_restaurant_by_id ::: returning restaurant={restaurant}")
        return Response(status_code=http200, body=restaurant)

    @utils_app.request_exception_handler
    @utils_app.log_start_finish
    def endpoint_get_delivery_price(self, address) -> Response:
        delivery_price = self.get_delivery_price(address)
        logger.info(f"endpoint_get_restaurant_by_id ::: restaurant_id={self.id_}, "
                    f"restaurant_address={self.address}, delivery_price={delivery_price}")
        return Response(status_code=http200, body={'delivery_price': delivery_price})

    @utils_app.request_exception_handler
    @utils_app.log_start_finish
    def endpoint_create_restaurant(self) -> Response:
        self.create_new_restaurant()
        return Response(status_code=http200, body={'message': 'Restaurant successfully created', 'id': self.id_})

    @utils_app.request_exception_handler
    @utils_app.log_start_finish
    def endpoint_update_restaurant(self) -> Response:
        self.update_restaurant()
        return Response(status_code=http200, body={'message': 'Restaurant was successfully updated', 'id': self.id_})

    def _get_restaurant_pk_sk(self) -> Tuple[str, str]:
        return self.pk, self.sk.format(restaurant_id=self.id_)

    def _get_restaurant_db_item(self):
        return utils_db.get_db_item(*self._get_restaurant_pk_sk())

    def _restaurant_update_white_fields_list(self):
        return list(self.required_mutable_fields_validation.keys())

    def to_dict(self):
        return {
            'id_': self.id_,
            'title': self.title,
            'address': self.address,
            'description': self.description,
            'cuisine': self.cuisine,
            'opening_time': self.opening_time,
            'closing_time': self.closing_time,
            'settings': self.settings,
            'status_': self.status_,
            "date_created": self.date_created,
            "date_updated": self.date_updated,
            'created_by': self.created_by,
            'updated_by': self.updated_by,
            "archived": self.archived
        }

    def _init_new_restaurant_db_record(self):
        pk, sk = self._get_restaurant_pk_sk()
        self.db_record = {
            'partkey': pk,
            'sortkey': sk,
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

    def create_new_restaurant(self):
        self._init_new_restaurant_db_record()
        self.validate_mandatory_fields()
        utils_db.put_db_record(self.db_record)
        logger.info(f"create_new_restaurant ::: restaurant {self.id_} successfully created")

    def validate_mandatory_fields_update(self, update_dict):
        clean_dict = {}
        for key, value in update_dict.items():
            if key in self.required_mutable_fields_validation and \
                    self.required_mutable_fields_validation[key](value) is True:
                clean_dict[key] = value
            else:
                logger.warning(f'update_fields_validation ::: key={key}, value={value} is not valid, '
                               f'removing from update dict..')
        return clean_dict

    def update_restaurant(self):
        pk, sk = self._get_restaurant_pk_sk()
        self.date_updated = datetime.now().isoformat(timespec="seconds")
        self.updated_by = self.request_data.get('auth_result', {}).get('user_id')
        update_dict = self.validate_mandatory_fields_update(self.to_dict())
        substitute_keys(dict_to_process=update_dict, base_keys=to_db)
        utils_db.update_db_record(
            key={'partkey': pk, 'sortkey': sk},
            update_body=update_dict,
            allowed_attrs_to_update=self._restaurant_update_white_fields_list(),
            allowed_attrs_to_delete=[]
        )
        logger.info(f"update_restaurant ::: restaurant {self.id_} was successfully updated")

    def to_ui(self):
        restaurant = self.to_dict()
        substitute_keys(dict_to_process=restaurant, base_keys=from_db)
        restaurant['settings']['category_sequence'] = {
            int(key): value for key, value in restaurant.get('settings', {}).get('category_sequence', {}).items()
        }
        return restaurant

    def get_delivery_price(self, delivery_address):
        """
        To be implemented
        """
        if not delivery_address:
            raise WrongDeliveryAddress('Provided delivery address is wrong')
        rest_address = self.address
        return Decimal(0).quantize(Decimal('1.00'))
