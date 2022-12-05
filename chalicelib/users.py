from datetime import datetime
from typing import Tuple

from chalice import Response

from chalicelib.constants import keys_structure
from chalicelib.constants.status_codes import http200
from chalicelib.constants.substitute_keys import from_db, to_db
from chalicelib.utils import db as utils_db, auth as utils_auth, app as utils_app, data as utils_data
from chalicelib.utils.data import substitute_keys
from chalicelib.utils.logger import logger


class User:
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

    def __init__(self, id_, **kwargs):
        self.id_ = id_
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

    @classmethod
    def init_by_id(cls, id_):
        c = cls(id_)
        c.__init__(**c._get_db_item())
        return c

    @classmethod
    @utils_auth.authenticate_class
    def init_request(cls, request):
        return cls.init_by_id(request.to_dict().get('auth_result', {}).get('user_id'))

    @classmethod
    @utils_auth.authenticate_class
    def init_request_get(cls, request):
        logger.info("init_request_get ::: started")
        return cls.init_by_id(request.to_dict().get('auth_result', {}).get('user_id'))

    @classmethod
    @utils_auth.authenticate_class
    def init_request_update(cls, request):
        logger.info("init_request_update ::: started")
        request_body = utils_data.parse_raw_body(request)
        id_ = request.to_dict().get('auth_result', {}).get('user_id')
        return cls(id_=id_, **request_body)

    @utils_app.request_exception_handler
    @utils_app.log_start_finish
    def endpoint_get_user(self) -> Response:
        return Response(status_code=http200, body=self.to_ui())

    @utils_app.request_exception_handler
    @utils_app.log_start_finish
    def endpoint_update_user(self) -> Response:
        self.update_user()
        return Response(status_code=http200, body={'message': 'User was successfully updated', 'id': self.id_})

    def _get_pk_sk(self) -> Tuple[str, str]:
        return self.pk, self.sk.format(user_id=self.id_)

    def _get_db_item(self):
        return utils_db.get_db_item(*self._get_pk_sk())

    def _update_white_fields_list(self):
        return [*self.required_mutable_fields_validation.keys(), *self.optional_fields_validation.keys()]

    def to_dict(self):
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

    def update_fields_validation(self, update_dict):
        clean_dict = {}
        validation_dict = {**self.required_mutable_fields_validation, **self.optional_fields_validation}
        for key, value in update_dict.items():
            if key in validation_dict and validation_dict[key](value) is True:
                clean_dict[key] = value
            else:
                logger.warning(f'update_fields_validation ::: key={key}, value={value} is not valid, '
                               f'removing from update dict..')
        return clean_dict

    def update_user(self):
        pk, sk = self._get_pk_sk()
        self.date_updated = datetime.now().isoformat(timespec="seconds")
        update_dict = self.update_fields_validation(self.to_dict())
        substitute_keys(dict_to_process=update_dict, base_keys=to_db)
        utils_db.update_db_record(
            key={'partkey': pk, 'sortkey': sk},
            update_body=update_dict,
            allowed_attrs_to_update=self._update_white_fields_list(),
            allowed_attrs_to_delete=[]
        )
        logger.info(f"update_user ::: user {self.id_} was successfully updated")

    def to_ui(self):
        user = self.to_dict()
        substitute_keys(dict_to_process=user, base_keys=from_db)
        return user
