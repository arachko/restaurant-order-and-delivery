from datetime import datetime
from typing import Tuple, Dict, List, Any

from chalicelib.constants.substitute_keys import from_db, to_db
from chalicelib.utils import db as utils_db
from chalicelib.utils.data import substitute_keys
from chalicelib.utils.logger import logger


class EntityBase:
    pk = None
    sk = None

    required_immutable_fields_validation = {}
    required_mutable_fields_validation = {}
    optional_fields_validation = {}

    def __init__(self, company_id, id_):
        self.company_id = company_id
        self.id_: str = id_
        self.record_type: str = ''
        self.request_data: Any[Dict, None] = None

    def _get_pk_sk(self) -> Tuple[str, str]:
        """
        Should be re-implemented in each child class
        :return:
        partkey, sortkey of db item for child
        """
        return self.pk, self.sk

    def _get_db_item(self) -> Dict:
        return utils_db.get_db_item(*self._get_pk_sk())

    def _to_dict(self) -> Dict:
        """
        Should be re-implemented in each child class
        :return:
        dict of item's attributes
        """
        return {
            'id_': self.id_,
            'record_type': self.record_type
        }

    def _init_db_record(self) -> None:
        """
        New DB record initialization
        :return:
        None
        """
        pk, sk = self._get_pk_sk()
        self.db_record = {
            'partkey': pk,
            'sortkey': sk,
            'company_id': self.company_id,
            'record_type': self.record_type,
            **self._to_dict()
        }

    def _validate_mandatory_fields(self):
        """
        Validates mandatory fields if all fields have correct type to put to db
        Raise ValidationException in case if a field is not valid
        :return:
        None
        """
        pass

    def _validate_optional_fields(self):
        """
        Validates optional fields if all fields have correct type to put to db
        Raise ValidationException in case if a field is not valid
        :return:
        None
        """
        pass

    def _get_validated_update_dict(self) -> Dict:
        """
        Validates fields for update
        Delete field if it is not valid
        :return:
        Clean dict for update
        (all invalid fields will be automatically excluded)
        """
        update_dict = self._to_dict()
        clean_dict = {}
        validation_dict = {**self.required_mutable_fields_validation, **self.optional_fields_validation}
        for key, value in update_dict.items():
            if key in validation_dict and validation_dict[key](value) is True:
                clean_dict[key] = value
            else:
                logger.warning(f'_get_validated_update_dict ::: {key=}, {value=} is not valid, '
                               f'removing from update dict..')
        return clean_dict

    def _create_db_record(self) -> None:
        """
        Creates entity db record
        :return:
        None
        """
        self._init_db_record()
        self._validate_mandatory_fields()
        self._validate_optional_fields()
        utils_db.put_db_record(self.db_record)
        logger.info(f"_create_db_record ::: {self.record_type=} {self.id_=} {self.db_record.get('partkey')=} "
                    f"{self.db_record.get('sortkey')=} successfully created")

    def _update_fields_whitelist(self) -> List:
        return [*self.required_mutable_fields_validation.keys(), *self.optional_fields_validation.keys()]

    def _update_db_record(self):
        """
        Updates entity db record
        :return:
        None
        """
        pk, sk = self._get_pk_sk()
        self.date_updated = datetime.now().isoformat(timespec="seconds")
        if self.request_data is not None:
            self.updated_by = self.request_data.get('auth_result', {}).get('user_id')
        update_dict = self._get_validated_update_dict()
        substitute_keys(dict_to_process=update_dict, base_keys=to_db)
        utils_db.update_db_record(
            key={'partkey': pk, 'sortkey': sk},
            update_body=update_dict,
            allowed_attrs_to_update=self._update_fields_whitelist(),
            allowed_attrs_to_delete=[]
        )
        logger.info(f"_update_db_record ::: {self.record_type=} "
                    f"{self.id_=} {pk=} {sk=} successfully updated")

    def _to_ui(self) -> Dict:
        item = self._to_dict()
        substitute_keys(dict_to_process=item, base_keys=from_db)
        return item
