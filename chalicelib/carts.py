from decimal import Decimal
from typing import Tuple

from chalice import Response

from chalicelib.constants import keys_structure
from chalicelib.constants.status_codes import http200
from chalicelib.constants.substitute_keys import to_db, from_db
from chalicelib.menu_items import MenuItem
from chalicelib.utils import auth as utils_auth, db as utils_db, app as utils_app, data as utils_data
from chalicelib.utils.data import substitute_keys
from chalicelib.utils.exceptions import RecordNotFound
from chalicelib.utils.logger import logger


class Cart:
    pk = keys_structure.carts_pk
    sk = keys_structure.carts_sk

    required_immutable_fields_validation = {
        'user_id': lambda x: isinstance(x, str),
        'restaurant_id': lambda x: isinstance(x, str),
    }

    required_mutable_fields_validation = {
        'item_ids': lambda x: isinstance(x, list),
        'delivery_address': lambda x: isinstance(x, str)
    }

    def __init__(self, user_id, address=None):
        self.user_id = user_id

        self.db_record: dict = {}
        self.restaurant_id = None
        self.delivery_address = address
        self.item_ids = []

    @classmethod
    def init_by_user_id(cls, user_id):
        c = cls(user_id=user_id)
        c._fill_db_item()
        return c

    @classmethod
    @utils_auth.authenticate_class
    def init_endpoint(cls, request):
        logger.info("init_request_cart ::: started")
        return cls(
            user_id=request.to_dict().get('auth_result', {}).get('user_id'),
            address=utils_data.parse_raw_body(request).get('address', None)
        )

    @utils_app.request_exception_handler
    @utils_app.log_start_finish
    def endpoint_get_cart(self):
        self._fill_db_item()
        return Response(status_code=http200, body={'cart': self.to_ui()})

    @utils_app.request_exception_handler
    @utils_app.log_start_finish
    def endpoint_add_item_to_cart(self, restaurant_id, menu_item_id):
        self._fill_db_item()
        if restaurant_id != self.restaurant_id:
            self.restaurant_id = restaurant_id
            self._init_db_record()
            self._put_db_record()
        self.item_ids.append(menu_item_id)
        all_items_available: bool = self.check_and_update_available_items()
        self._update_item_list_in_db()
        notice_to_ui = 'Some items are not longer available and were deleted from the cart' if not all_items_available else None
        return Response(status_code=http200, body={'cart': self.to_ui(), 'message': notice_to_ui})

    @utils_app.request_exception_handler
    @utils_app.log_start_finish
    def endpoint_remove_item_from_cart(self, menu_item_id):
        self._fill_db_item()
        self.item_ids.remove(menu_item_id)
        self._update_item_list_in_db()
        return Response(status_code=http200, body={'cart': self.to_ui()})

    @utils_app.request_exception_handler
    @utils_app.log_start_finish
    def endpoint_clear_cart(self):
        self.delete_db_record()
        return Response(status_code=http200, body={'message': 'Cart was successfully cleared'})

    def _get_pk_sk(self) -> Tuple[str, str]:
        return self.pk, self.sk.format(user_id=self.user_id)

    def to_dict(self):
        return {
            'user_id': self.user_id,
            'restaurant_id': self.restaurant_id,
            'delivery_address': self.delivery_address,
            'item_ids': self.item_ids
        }

    def _init_db_record(self):
        pk, sk = self._get_pk_sk()
        self.db_record = {
            'partkey': pk,
            'sortkey': sk,
            **self.to_dict()
        }

    def _fill_db_item(self):
        try:
            self.db_record = utils_db.get_db_item(*self._get_pk_sk())
            self.restaurant_id = self.db_record.get('restaurant_id')
            self.delivery_address = self.db_record.get('delivery_address')
            self.item_ids = self.db_record.get('item_ids')
        except RecordNotFound:
            self._init_db_record()

    def _put_db_record(self):
        substitute_keys(dict_to_process=self.db_record, base_keys=to_db)
        utils_db.put_db_record(self.db_record)

    def to_ui(self):
        menu_item = self.to_dict()
        substitute_keys(dict_to_process=menu_item, base_keys=from_db)
        return menu_item

    def check_and_update_available_items(self) -> bool:
        items_num = len(self.item_ids)
        self.item_ids = [item_id for item_id in self.item_ids if
                         MenuItem.init_get_by_id(item_id, self.restaurant_id).is_available]
        return True if items_num == len(self.item_ids) else False

    def _update_white_fields_list(self):
        return list(self.required_mutable_fields_validation)

    def _update_item_list_in_db(self):
        pk, sk = self._get_pk_sk()
        utils_db.update_db_record(
            key={'partkey': pk, 'sortkey': sk},
            update_body={'item_ids': self.item_ids},
            allowed_attrs_to_update=self._update_white_fields_list(),
            allowed_attrs_to_delete=[]
        )
        logger.info(f"update_item_list_in_db ::: item list in the cart was successfully updated")

    def delete_db_record(self):
        pk, sk = self._get_pk_sk()
        utils_db.get_gen_table().delete_item(Key={'partkey': pk, 'sortkey': sk})
        logger.info(f"delete_db_record ::: item list in the cart was successfully updated")
