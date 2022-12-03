from datetime import datetime
from decimal import Decimal
from typing import List, Dict, Tuple
from uuid import uuid4

from boto3.dynamodb.conditions import Attr, Key
from chalice import Response

from chalicelib.constants import keys_structure
from chalicelib.constants.status_codes import http200
from chalicelib.constants.substitute_keys import to_db, from_db
from chalicelib.utils import auth as utils_auth, data as utils_data, exceptions, db as utils_db, app as utils_app
from chalicelib.utils.data import substitute_keys
from chalicelib.utils.logger import logger


class MenuItem:
    pk = keys_structure.menu_items_pk
    sk = keys_structure.menu_items_sk

    required_immutable_fields_validation = {
        'id_': lambda x: isinstance(x, str),
        'created_by': lambda x: isinstance(x, str),
        "date_created": lambda x: isinstance(x, str)
    }

    required_mutable_fields_validation = {
        'title': lambda x: isinstance(x, str),
        'category': lambda x: isinstance(x, str),
        'description': lambda x: isinstance(x, str),
        'price': lambda x: isinstance(x, Decimal),
        'is_available': lambda x: isinstance(x, bool),
        "date_updated": lambda x: isinstance(x, str),
        "updated_by": lambda x: isinstance(x, str),
        "archived": lambda x: isinstance(x, bool)
    }

    optional_fields_validation = {
        'opening_time': lambda x: isinstance(x, Decimal),
        'closing_time': lambda x: isinstance(x, Decimal),
        'weight': lambda x: isinstance(x, Decimal),
        'options': lambda x: isinstance(x, list)
    }

    def __init__(self, id_, restaurant_id, **kwargs):
        self.request_data = kwargs.get('request_data', {})
        self.db_record: dict = {}

        self.id_: str = id_
        self.restaurant_id: str = restaurant_id
        self.title: str = kwargs.get('title')
        self.category: str = kwargs.get('category')
        self.description: str = kwargs.get('description')
        self.price: Decimal = Decimal(kwargs.get('price')).quantize(Decimal('1.00')) if \
            type(kwargs.get('price')) in [int, float, Decimal] else None
        self.opening_time: Decimal = Decimal(kwargs.get('opening_time')).quantize(Decimal('1')) if \
            type(kwargs.get('opening_time')) in [int, Decimal] else None
        self.closing_time: Decimal = Decimal(kwargs.get('closing_time')).quantize(Decimal('1')) if \
            type(kwargs.get('closing_time')) in [int, Decimal] else None
        self.weight: Decimal = Decimal(kwargs.get('weight')).quantize(Decimal('1')) if \
            type(kwargs.get('weight')) in [int, Decimal] else None
        self.options: list = kwargs.get('options', [])
        self.is_available: str = kwargs.get('is_available', True)
        self.created_by: str = kwargs.get('created_by') or self.request_data.get('auth_result', {}).get('user_id')
        self.updated_by: str = kwargs.get('updated_by') or self.request_data.get('auth_result', {}).get('user_id')
        self.date_created: str = kwargs.get('date_created') or datetime.now().isoformat(timespec="seconds")
        self.date_updated: str = kwargs.get('date_updated') or datetime.now().isoformat(timespec="seconds")
        self.archived: bool = kwargs.get('archived', False)

    @classmethod
    @utils_auth.authenticate_class
    def init_request_create_update(cls, request, restaurant_id, menu_item_id=None, special_body=None):
        logger.info("init_request_create_update ::: started")
        request_body = special_body or utils_data.parse_raw_body(request)
        id_ = menu_item_id or str(uuid4())
        return cls(id_=id_, restaurant_id=restaurant_id, request_data=request.to_dict(), **request_body)

    @classmethod
    def init_get_by_id(cls, menu_item_id, restaurant_id):
        logger.info("init_get_by_id ::: started")
        c = cls(id_=menu_item_id, restaurant_id=restaurant_id)
        c.__init__(**c._get_db_item())
        return c

    @staticmethod
    @utils_app.log_start_finish
    def endpoint_get_menu_items(request, restaurant_id) -> Response:
        filter_expression = Attr('archived').eq(False)
        menu_item_db_records: List[Dict] = utils_db.query_items_paged(
            Key('partkey').eq(keys_structure.menu_items_pk.format(restaurant_id=restaurant_id)),
            filter_expression=filter_expression
        )
        menu_items: List[Dict] = [MenuItem(**record).to_ui() for record in menu_item_db_records]
        logger.info(f"endpoint_get_restaurants ::: returning menu items={[rest['id'] for rest in menu_items]}")
        return Response(status_code=http200, body=menu_items)

    @utils_app.request_exception_handler
    @utils_app.log_start_finish
    def endpoint_create_menu_item(self) -> Response:
        self.create_menu_item()
        return Response(status_code=http200, body={'message': 'Menu item successfully created', 'id': self.id_})

    @utils_app.request_exception_handler
    @utils_app.log_start_finish
    def endpoint_update_menu_item(self) -> Response:
        self.update_menu_item()
        return Response(status_code=http200, body={'message': 'Menu item successfully updated', 'id': self.id_})

    def _get_pk_sk(self) -> Tuple[str, str]:
        return self.pk.format(restaurant_id=self.restaurant_id), self.sk.format(menu_item_id=self.id_)

    def _get_db_item(self):
        return utils_db.get_db_item(*self._get_pk_sk())

    def _update_white_fields_list(self):
        return [*self.required_mutable_fields_validation.keys(), *self.optional_fields_validation.keys()]

    def is_available_right_now(self):
        # Todo: add opening-closing time check
        return self.is_available

    def to_dict(self):
        return {
            'id_': self.id_,
            'restaurant_id': self.restaurant_id,
            'title': self.title,
            'category': self.category,
            'description': self.description,
            'price': self.price,
            'opening_time': self.opening_time,
            'closing_time': self.closing_time,
            'is_available': self.is_available,
            "date_created": self.date_created,
            "date_updated": self.date_updated,
            'created_by': self.created_by,
            'updated_by': self.updated_by,
            "archived": self.archived,
            'weight': self.weight,
            'options': self.options
        }

    def _init_db_record(self):
        pk, sk = self._get_pk_sk()
        self.db_record = {
            'partkey': pk,
            'sortkey': sk,
            **self.to_dict()
        }
        substitute_keys(dict_to_process=self.db_record, base_keys=to_db)

    @staticmethod
    def raise_validation_error(key):
        message = f'Validation error occurred while validating field={key}'
        logger.error(f"raise_validation_error ::: {message}")
        raise exceptions.ValidationException(message)

    def validate_mandatory_fields(self):
        for key, validator_func in {
            **self.required_immutable_fields_validation,
            **self.required_mutable_fields_validation
        }.items():
            if validator_func(self.db_record.get(key)) is False:
                self.raise_validation_error(key)

    def validate_optional_fields(self):
        for key, validator_func in self.optional_fields_validation.items():
            if self.db_record.get(key) is not None and validator_func(self.db_record.get(key)) is False:
                self.raise_validation_error(key)

    def create_menu_item(self):
        self._init_db_record()
        self.validate_mandatory_fields()
        self.validate_optional_fields()
        utils_db.put_db_record(self.db_record)
        logger.info(f"create_new_menu_item ::: menu_item {self.id_} successfully created")

    def validate_fields_update(self, update_dict):
        clean_dict = {}
        for key, value in update_dict.items():
            if key in self.required_mutable_fields_validation and \
                    self.required_mutable_fields_validation[key](value) is True:
                clean_dict[key] = value
            elif key in self.optional_fields_validation and \
                    self.optional_fields_validation[key](value) is True:
                clean_dict[key] = value
            else:
                logger.warning(f'update_fields_validation ::: key={key}, value={value} is not valid, '
                               f'removing from update dict..')
        return clean_dict

    def update_menu_item(self):
        pk, sk = self._get_pk_sk()
        self.date_updated = datetime.now().isoformat(timespec="seconds")
        self.updated_by = self.request_data.get('auth_result', {}).get('user_id')
        update_dict = self.validate_fields_update(self.to_dict())
        substitute_keys(dict_to_process=update_dict, base_keys=to_db)
        utils_db.update_db_record(
            key={'partkey': pk, 'sortkey': sk},
            update_body=update_dict,
            allowed_attrs_to_update=self._update_white_fields_list(),
            allowed_attrs_to_delete=[]
        )
        logger.info(f"update_menu_item ::: menu_item {self.id_} successfully updated")

    def to_ui(self):
        menu_item = self.to_dict()
        substitute_keys(dict_to_process=menu_item, base_keys=from_db)
        return menu_item

