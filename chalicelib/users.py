from typing import Tuple

from chalicelib.constants import keys_structure
from chalicelib.utils import db as utils_db


class User:
    pk = keys_structure.users_pk
    sk = keys_structure.users_sk

    required_immutable_fields_validation = {
        'id_': lambda x: isinstance(x, str),
        'login': lambda x: isinstance(x, str),  # EMAIL or PHONE NUMBER
        'phone': lambda x: isinstance(x, str),
        'role': lambda x: isinstance(x, str),
        'date_created': lambda x: isinstance(x, str)
    }

    required_mutable_fields_validation = {
        'date_updated': lambda x: isinstance(x, str)
    }

    optional_fields_validation = {
        'first_name': lambda x: isinstance(x, str),
        'last_name': lambda x: isinstance(x, str),
        'email': lambda x: isinstance(x, str),
        'addresses': lambda x: isinstance(x, list),
        'additional_phone_numbers': lambda x: isinstance(x, list)
    }

    def __init__(self, id_, **kwargs):
        self.id_ = id_
        self.login = kwargs.get('login', [])
        self.phone = kwargs.get('phone', [])
        self.role = kwargs.get('role')
        self.first_name = kwargs.get('first_name')
        self.last_name = kwargs.get('last_name')
        self.email = kwargs.get('email')
        self.addresses = kwargs.get('addresses', [])
        self.phone_numbers = kwargs.get('phone_numbers', [])

    @classmethod
    def init_by_id(cls, id_):
        c = cls(id_)
        c.__init__(**c._get_db_item())
        return c

    def _get_pk_sk(self) -> Tuple[str, str]:
        return self.pk, self.sk.format(user_id=self.id_)

    def _get_db_item(self):
        return utils_db.get_db_item(*self._get_pk_sk())
