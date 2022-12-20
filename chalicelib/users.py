from typing import Tuple

from chalice import Response

from chalicelib.base_class_entity import EntityBase
from chalicelib.constants import keys_structure
from chalicelib.constants.status_codes import http200
from chalicelib.utils import auth as utils_auth, app as utils_app, data as utils_data
from chalicelib.utils.logger import logger


class User(EntityBase):
    pk = keys_structure.users_pk
    sk = keys_structure.users_sk

    required_immutable_fields_validation = {
        'id_': lambda x: isinstance(x, str),
        'login': lambda x: isinstance(x, str),  # EMAIL or PHONE NUMBER
        'phone': lambda x: isinstance(x, str),
        'email': lambda x: isinstance(x, str),
        'role': lambda x: isinstance(x, str),
        'date_created': lambda x: isinstance(x, str)
    }

    required_mutable_fields_validation = {
        'date_updated': lambda x: isinstance(x, str)
    }

    optional_fields_validation = {
        'first_name': lambda x: isinstance(x, str),
        'last_name': lambda x: isinstance(x, str),
        'addresses': lambda x: isinstance(x, list),
        'additional_phone_numbers': lambda x: isinstance(x, list)
    }

    def __init__(self, company_id, id_, **kwargs):
        EntityBase.__init__(self, company_id, id_)

        self.login = kwargs.get('login')
        self.phone = kwargs.get('phone', [])
        self.role = kwargs.get('role')
        self.first_name = kwargs.get('first_name')
        self.last_name = kwargs.get('last_name')
        self.email = kwargs.get('email')
        self.addresses = kwargs.get('addresses', [])
        self.phone_numbers = kwargs.get('phone_numbers', [])
        self.additional_phone_numbers = kwargs.get('additional_phone_numbers', [])
        self.date_created = kwargs.get('date_created')
        self.date_updated = kwargs.get('date_updated')
        self.record_type = 'user'

    @classmethod
    def init_by_id(cls, company_id, id_):
        logger.info("init_endpoint ::: started")
        c = cls(company_id, id_)
        c.__init__(**c._get_db_item())
        return c

    @classmethod
    @utils_auth.authenticate_class
    def init_request_get(cls, request):
        logger.info("init_request_get ::: started")
        auth_result = request.auth_result
        return cls.init_by_id(auth_result['company_id'], auth_result['user_id'])

    @classmethod
    @utils_auth.authenticate_class
    def init_request_update(cls, request):
        logger.info("init_request_update ::: started")
        auth_result = request.auth_result
        request_body = utils_data.parse_raw_body(request)
        return cls(company_id=auth_result['company_id'], id_=auth_result['user_id'], **request_body)

    @utils_app.request_exception_handler
    @utils_app.log_start_finish
    def endpoint_get_user(self) -> Response:
        return Response(status_code=http200, body=self._to_ui())

    @utils_app.request_exception_handler
    @utils_app.log_start_finish
    def endpoint_update_user(self) -> Response:
        self._update_db_record()
        return Response(status_code=http200, body={'message': 'User was successfully updated', 'id': self.id_})

    def _get_pk_sk(self) -> Tuple[str, str]:
        return self.pk.format(company_id=self.company_id), self.sk.format(user_id=self.id_)

    def _to_dict(self):
        return {
            'id_': self.id_,
            'login': self.login,
            'phone': self.phone,
            'role': self.role,
            'date_created': self.date_created,
            'date_updated': self.date_updated,
            'first_name': self.first_name,
            'last_name': self.last_name,
            'email': self.email,
            'addresses': self.addresses,
            'additional_phone_numbers': self.additional_phone_numbers
        }
