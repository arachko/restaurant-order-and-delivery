from datetime import datetime
from decimal import Decimal
from typing import List, Dict, Tuple
from uuid import uuid4

from boto3.dynamodb.conditions import Attr, Key
from chalice import Response

from chalicelib.base_class_entity import EntityBase
from chalicelib.constants import keys_structure
from chalicelib.constants.status_codes import http200
from chalicelib.utils import auth as utils_auth, data as utils_data, exceptions, db as utils_db, app as utils_app
from chalicelib.utils.auth import get_company_id_by_request
from chalicelib.utils.logger import logger


class MenuItem(EntityBase):
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

    def __init__(self, company_id, id_, restaurant_id, **kwargs):
        EntityBase.__init__(self, company_id, id_)

        self.request_data = kwargs.get('request_data', {})
        self.db_record: dict = {}

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
        self.is_available: bool = kwargs.get('is_available', True)
        self.created_by: str = kwargs.get('created_by') or self.request_data.get('auth_result', {}).get('user_id')
        self.updated_by: str = kwargs.get('updated_by') or self.request_data.get('auth_result', {}).get('user_id')
        self.date_created: str = kwargs.get('date_created') or datetime.now().isoformat(timespec="seconds")
        self.date_updated: str = kwargs.get('date_updated') or datetime.now().isoformat(timespec="seconds")
        self.archived: bool = kwargs.get('archived', False)
        self.record_type = 'menu_item'

    @classmethod
    @utils_auth.authenticate_class
    def init_request_create_update(cls, request, restaurant_id, menu_item_id=None, special_body=None):
        logger.info("init_request_create_update ::: started")
        company_id = get_company_id_by_request(request)
        request_body = special_body or utils_data.parse_raw_body(request)
        id_ = menu_item_id or str(uuid4())
        return cls(company_id=company_id, id_=id_, restaurant_id=restaurant_id,
                   request_data=request.to_dict(), **request_body)

    @classmethod
    def init_get_by_id(cls, company_id, menu_item_id, restaurant_id):
        logger.info("init_get_by_id ::: started")
        c = cls(company_id=company_id, id_=menu_item_id, restaurant_id=restaurant_id)
        c.__init__(**c._get_db_item())
        return c

    @staticmethod
    @utils_app.log_start_finish
    def endpoint_get_menu_items(request, restaurant_id) -> Response:
        company_id = get_company_id_by_request(request)
        filter_expression = Attr('archived').eq(False)
        menu_item_db_records: List[Dict] = utils_db.query_items_paged(
            Key('partkey').eq(keys_structure.menu_items_pk.format(company_id=company_id, restaurant_id=restaurant_id)),
            filter_expression=filter_expression
        )
        menu_items: List[Dict] = [MenuItem(**record)._to_ui() for record in menu_item_db_records]
        logger.info(f"endpoint_get_restaurants ::: returning menu items={[rest['id'] for rest in menu_items]}")
        return Response(status_code=http200, body=menu_items)

    @utils_app.request_exception_handler
    @utils_app.log_start_finish
    def endpoint_create_menu_item(self) -> Response:
        self._create_db_record()
        return Response(status_code=http200, body={'message': 'Menu item successfully created', 'id': self.id_})

    @utils_app.request_exception_handler
    @utils_app.log_start_finish
    def endpoint_update_menu_item(self) -> Response:
        self._update_db_record()
        return Response(status_code=http200, body={'message': 'Menu item was successfully updated', 'id': self.id_})

    def _get_pk_sk(self) -> Tuple[str, str]:
        return self.pk.format(company_id=self.company_id, restaurant_id=self.restaurant_id), \
            self.sk.format(menu_item_id=self.id_)

    def is_available_right_now(self) -> bool:
        # Todo: add opening-closing time check
        return self.is_available

    def _to_dict(self):
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

    @staticmethod
    def raise_validation_error(key):
        message = f'Validation error occurred while validating field={key}'
        logger.error(f"raise_validation_error ::: {message}")
        raise exceptions.ValidationException(message)

    def _validate_mandatory_fields(self):
        for key, validator_func in {
            **self.required_immutable_fields_validation,
            **self.required_mutable_fields_validation
        }.items():
            if validator_func(self.db_record.get(key)) is False:
                self.raise_validation_error(key)

    def _validate_optional_fields(self):
        for key, validator_func in self.optional_fields_validation.items():
            if self.db_record.get(key) is not None and validator_func(self.db_record.get(key)) is False:
                self.raise_validation_error(key)

    def to_ui(self):
        return self._to_ui()
