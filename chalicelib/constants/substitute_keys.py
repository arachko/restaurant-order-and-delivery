to_db = {
    'name': "name_",
    'id': "id_",
    'status': 'status_',
    'items': 'items_',
    'comment': 'comment_'
}

from_db = {
    'name_': "name",
    'id_': "id",
    'status_': 'status',
    'items_': 'items',
    'comment_': 'comment',
    'partkey': None,
    'sortkey': None
}


# def replace_dict_key(item, orig_key, new_key):
#     if orig_key in item:
#         if new_key not in item:
#             item[new_key] = item[orig_key]
#         del item[orig_key]
#
# def to_db(item):
#     replace_dict_key(item, 'id', 'id_')
#     replace_dict_key(item, 'name', 'name_')
#
#
# def from_db(item):
#     item.pop('partkey', None)
#     item.pop('sortkey', None)
#     replace_dict_key(item, 'id_', 'id')
#     replace_dict_key(item, 'name_', 'name')