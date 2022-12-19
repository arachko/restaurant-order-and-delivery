users_pk = 'users_{company_id}'
users_sk = '{user_id}'

restaurants_pk = 'restaurants_{company_id}'
restaurants_sk = '{restaurant_id}'

menu_items_pk = 'menu_items_{company_id}_{restaurant_id}'
menu_items_sk = '{menu_item_id}'

carts_pk = 'carts_{company_id}'
carts_sk = '{user_id}'

pre_orders_pk = 'pre_order_{company_id}_{user_id}'
pre_orders_sk = '{order_id}'

orders_pk = 'orders_{company_id}_{restaurant_id}'
orders_sk = '{user_id}_{order_id}'

orders_archived_pk = 'orders_archived_{company_id}_{restaurant_id}'
orders_archived_sk = '{user_id}_{order_id}'

gsi_user_orders_pk = 'orders_{company_id}_{user_id}'
gsi_user_orders_sk = '{restaurant_id}_{order_id}'

gsi_orders_archived_pk = 'orders_archived_{company_id}_{user_id}'
gsi_orders_archived_sk = '{restaurant_id}_{order_id}'
