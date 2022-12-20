from typing import Tuple, List, Dict, Any

from chalice import Response

from chalicelib.base_class_entity import EntityBase
from chalicelib.constants import keys_structure
from chalicelib.constants.status_codes import http200
from chalicelib.menu_items import MenuItem
from chalicelib.utils import auth as utils_auth, db as utils_db, app as utils_app, data as utils_data, exceptions
from chalicelib.utils.logger import logger


class Cart(EntityBase):
    pk = keys_structure.carts_pk
    sk = keys_structure.carts_sk

    required_immutable_fields_validation = {
        'id_': lambda x: isinstance(x, str),
        'restaurant_id': lambda x: isinstance(x, str),
    }

    required_mutable_fields_validation = {
        'menu_items': lambda x: isinstance(x, dict),
        'delivery_address': lambda x: isinstance(x, str)
    }

    def __init__(self, company_id, id_, request_body=None):
        EntityBase.__init__(self, company_id, id_)

        if request_body is None:
            request_body = {}

        self.request_body = request_body
        self.db_record: Dict = {}
        self.restaurant_id: Any[str, None] = None
        self.delivery_address = request_body.get('address', None)
        self.menu_items: Dict = {}
        self.record_type: str = 'cart'

    def _fill_db_item(self):
        try:
            self.db_record = self._get_db_item()
            self.restaurant_id = self.db_record.get('restaurant_id')
            self.delivery_address = self.db_record.get('delivery_address')
            self.menu_items = self.db_record.get('menu_items')
        except exceptions.RecordNotFound:
            self._init_db_record()

    @classmethod
    def init_by_user_id(cls, company_id, user_id):
        c = cls(company_id=company_id, id_=user_id)
        c._fill_db_item()
        return c

    @classmethod
    @utils_auth.authenticate_class
    def init_endpoint(cls, request):
        logger.info("init_endpoint ::: started")
        auth_result = request.auth_result
        return cls(
            company_id=auth_result['company_id'],
            id_=request.auth_result.get('user_id'),
            request_body=utils_data.parse_raw_body(request)
        )

    @utils_app.request_exception_handler
    @utils_app.log_start_finish
    def endpoint_get_cart(self):
        self._fill_db_item()
        return Response(status_code=http200, body={'cart': self._to_ui()})

    @utils_app.request_exception_handler
    @utils_app.log_start_finish
    def endpoint_add_item_to_cart(self):
        self._fill_db_item()
        qty = self.request_body.get('qty')
        request_restaurant_id = self.request_body.get('restaurant_id')
        menu_item_id = self.request_body.get('menu_item_id')
        if request_restaurant_id != self.restaurant_id:
            self.restaurant_id = request_restaurant_id
            self._create_db_record()
            self.menu_items = {}
        self.menu_items[menu_item_id] = {'id': menu_item_id, 'qty': qty}
        all_items_available: bool = self._check_and_update_available_items()
        self._update_db_record()
        ui_message = None
        if not all_items_available:
            ui_message = 'Some items in your cart are not longer available and were deleted from the cart'
        return Response(status_code=http200, body={'cart': self._to_ui(), 'message': ui_message})

    @utils_app.request_exception_handler
    @utils_app.log_start_finish
    def endpoint_remove_item_from_cart(self, menu_item_id):
        self._fill_db_item()
        self.menu_items.pop(menu_item_id)
        self._update_db_record()
        return Response(status_code=http200, body={'cart': self._to_ui()})

    @utils_app.request_exception_handler
    @utils_app.log_start_finish
    def endpoint_clear_cart(self):
        self.delete_db_record()
        return Response(status_code=http200, body={'message': 'Cart was successfully cleared'})

    def _get_pk_sk(self) -> Tuple[str, str]:
        return self.pk.format(company_id=self.company_id), self.sk.format(user_id=self.id_)

    def _to_dict(self):
        return {
            'id_': self.id_,
            'restaurant_id': self.restaurant_id,
            'delivery_address': self.delivery_address,
            'menu_items': self.menu_items
        }

    def _check_and_update_available_items(self) -> bool:
        items_qnt = len(self.menu_items)
        self.menu_items = {item_id: info for item_id, info in self.menu_items.items() if
                           MenuItem.init_get_by_id(self.company_id, item_id, self.restaurant_id).is_available}
        return True if items_qnt == len(self.menu_items) else False

    def delete_db_record(self):
        pk, sk = self._get_pk_sk()
        utils_db.get_gen_table().delete_item(Key={'partkey': pk, 'sortkey': sk})
        logger.info(f"delete_db_record ::: item list in the cart was successfully updated")
