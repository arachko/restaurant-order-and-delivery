from datetime import datetime
from decimal import Decimal
from typing import Tuple, List, Dict
from uuid import uuid4

from boto3.dynamodb.conditions import Attr, Key
from chalice import Response

from chalicelib.base_class_entity import EntityBase
from chalicelib.constants import keys_structure
from chalicelib.constants.status_codes import http200
from chalicelib.constants.substitute_keys import from_db
from chalicelib.utils import auth as utils_auth, data as utils_data, exceptions, db as utils_db, app as utils_app
from chalicelib.utils.auth import get_company_id_by_request
from chalicelib.utils.data import substitute_keys
from chalicelib.utils.exceptions import WrongDeliveryAddress
from chalicelib.utils.logger import logger


class Restaurant(EntityBase):
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

    def __init__(self, company_id, id_, **kwargs):
        EntityBase.__init__(self, company_id, id_)

        self.request_data = kwargs.get('request_data', {})
        self.db_record: dict = {}

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
        self.record_type = 'restaurant'

    @classmethod
    @utils_auth.authenticate_class
    def init_request_create_update(cls, request, restaurant_id=None, special_body=None):
        logger.info("init_request_create_update ::: started")
        company_id = get_company_id_by_request(request)
        request_body = special_body or utils_data.parse_raw_body(request)
        id_ = restaurant_id or str(uuid4())
        return cls(company_id=company_id, id_=id_, request_data=request.to_dict(), **request_body)

    @classmethod
    def init_get_by_id(cls, company_id, restaurant_id):
        logger.info("init_request_get_by_id ::: started")
        c = cls(company_id, restaurant_id)
        c.__init__(**c._get_db_item())
        return c

    @staticmethod
    @utils_app.log_start_finish
    def endpoint_get_all(request) -> Response:
        logger.info("endpoint_get_all ::: started")
        company_id = get_company_id_by_request(request)
        filter_expression = Attr('archived').eq(False)
        restaurant_db_records: List[Dict] = utils_db.query_items_paged(
            Key('partkey').eq(keys_structure.restaurants_pk.format(company_id=company_id)),
            filter_expression=filter_expression
        )
        restaurants: List[Dict] = [Restaurant(**record)._to_ui() for record in restaurant_db_records]
        logger.info(f"endpoint_get_restaurants ::: returning restaurants={[rest['id'] for rest in restaurants]}")
        return Response(status_code=http200, body=restaurants)

    @utils_app.request_exception_handler
    @utils_app.log_start_finish
    def endpoint_get_by_id(self) -> Response:
        restaurant = self._to_ui()
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
    def endpoint_create(self) -> Response:
        self._create_db_record()
        return Response(status_code=http200, body={'message': 'Restaurant successfully created', 'id': self.id_})

    @utils_app.request_exception_handler
    @utils_app.log_start_finish
    def endpoint_update(self) -> Response:
        self._update_db_record()
        return Response(status_code=http200, body={'message': 'Restaurant was successfully updated', 'id': self.id_})

    def _get_pk_sk(self) -> Tuple[str, str]:
        return self.pk.format(company_id=self.company_id), self.sk.format(restaurant_id=self.id_)

    def _to_dict(self):
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

    def _to_ui(self):
        item = self._to_dict()
        item['settings']['category_sequence'] = {
            int(key): value for key, value in item.get('settings', {}).get('category_sequence', {}).items()
        }
        substitute_keys(dict_to_process=item, base_keys=from_db)
        return item

    def get_delivery_price(self, delivery_address):
        """
        To be implemented
        """
        if not delivery_address:
            raise WrongDeliveryAddress('Provided delivery address is wrong')
        rest_address = self.address
        return Decimal(0).quantize(Decimal('1.00'))
