users_pk = 'users_'
users_sk = '{user_id}'

restaurants_pk = 'restaurants_'
restaurants_sk = '{restaurant_id}'

menu_items_pk = 'menu_items_{restaurant_id}'
menu_items_sk = '{menu_item_id}'

carts_pk = 'carts_'
carts_sk = '{user_id}'

pre_orders_pk = 'pre_order_{user_id}'
pre_orders_sk = '{order_id}'

orders_pk = 'orders_{restaurant_id}'
orders_sk = '{user_id}_{order_id}'

orders_archived_pk = 'orders_archived_{restaurant_id}'
orders_archived_sk = '{user_id}_{order_id}'

gsi_user_orders_pk = 'orders_{user_id}'
gsi_user_orders_sk = '{order_id}'

gsi_orders_archived_pk = 'orders_archived_{user_id}'
gsi_orders_archived_sk = '{restaurant_id}_{order_id}'
