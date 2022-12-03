import json
from datetime import datetime, date
from decimal import Decimal
from time import struct_time, mktime


def replace_dict_key(item, orig_key, new_key):
    if orig_key in item:
        if new_key not in item:
            item[new_key] = item[orig_key]
        del item[orig_key]


def substitute_keys_to_db(item):
    replace_dict_key(item, 'id', 'id_')
    replace_dict_key(item, 'name', 'name_')


def substitute_keys_from_db(item):
    item.pop('partkey', None)
    item.pop('sortkey', None)
    replace_dict_key(item, 'id_', 'id')
    replace_dict_key(item, 'name_', 'name')


def substitute_keys(dict_to_process: dict, base_keys: dict, opt_dict=None):
    if opt_dict is None:
        opt_dict = {}
    all_keys = {**base_keys, **opt_dict}
    for key, val in all_keys.items():
        if val:
            replace_dict_key(dict_to_process, key, val)
        elif key in dict_to_process.keys():
            dict_to_process.pop(key, None)


def substitute_records(records_to_process, base_keys: dict, opt_dict: dict = None):
    for i, _ in enumerate(records_to_process):
        substitute_keys(
            dict_to_process=records_to_process[i],
            base_keys=base_keys,
            opt_dict=opt_dict
        )


def parse_raw_body(chalice_request):
    request_raw_body = chalice_request.raw_body
    if request_raw_body:
        return fix_values_from_ui(item=json.loads(request_raw_body))
    else:
        return {}


def fix_values_from_ui(item):
    """
    Remove keys with empty or None values and transform float to Decimal
    """
    if item.get('_values_from_ui_strategy') == 'delete_empty':
        list_to_cleanup = ['', None]
    else:
        list_to_cleanup = [None]
    item = cleanup_dict(item, list_to_cleanup)
    item.pop('_values_from_ui_strategy', None)
    result = json.dumps(item)
    return json.loads(result, parse_float=Decimal)


def cleanup_dict(item: dict, list_of_values: list):
    """ Remove None fields in dict with. Supports one nesting.  """

    def sub_clean(sub_item):
        return {
            key: value
            for key, value in sub_item.items()
            if value not in list_of_values
        }

    clean = {}
    for k, v in item.items():
        if isinstance(v, dict):
            nested = sub_clean(v)
            if len(nested.keys()) > 0:
                clean[k] = nested
        elif v not in list_of_values:
            clean[k] = v
    return clean
