import os

from chalice import Chalice

from chalicelib import auth, orders, carts, menu_items, restaurants, images, users, triggers
from chalicelib.constants.constants import UNAUTHORIZED_USER
from chalicelib.utils import data as utils_data

app = Chalice(app_name='restaurant-order-and-delivery')

app.api.binary_types.insert(0, 'multipart/form-data')
app.debug = True


def get_customers_table_stream_arn():
    return os.environ["CUSTOMERS_TABLE_STREAM_ARN"]


@app.authorizer()
def role_authorizer(auth_request):
    return auth.role_authorizer(auth_request)


@app.on_dynamodb_record(stream_arn=get_customers_table_stream_arn())
def db_customers_table_stream_trigger(event, context):
    return triggers.db_customers_table_stream_trigger(event, context)


# USERS
@app.route('/users', methods=['GET'], authorizer=role_authorizer, cors=True)
def get_user():
    return users.User.init_request_get(app.current_request).endpoint_get_user()


@app.route('/users', methods=['PUT'], authorizer=role_authorizer, cors=True)
def update_user():
    return users.User.init_request_update(app.current_request).endpoint_update_user()


# RESTAURANTS
@app.route('/restaurants', methods=['GET'], cors=True)
def get_restaurants():
    return restaurants.Restaurant.endpoint_get_all(app.current_request)


@app.route('/restaurants/{restaurant_id}', methods=['GET'], cors=True)
def get_restaurant_by_id(restaurant_id):
    return restaurants.Restaurant.init_get_by_id(restaurant_id).\
        endpoint_get_by_id()


@app.route('/restaurants/{restaurant_id}/delivery-price', methods=['POST'], cors=True)
def get_delivery_address(restaurant_id):
    address = utils_data.parse_raw_body(app.current_request).get('delivery_address')
    return restaurants.Restaurant.init_get_by_id(restaurant_id).\
        endpoint_get_delivery_price(address)


@app.route('/restaurants', methods=['POST'], authorizer=role_authorizer, cors=True)
def create_restaurant():
    """
    admin operation
    """
    return restaurants.Restaurant.init_request_create_update(app.current_request).endpoint_create()


@app.route('/restaurants/{restaurant_id}', methods=['PUT'], authorizer=role_authorizer, cors=True)
def update_restaurant(restaurant_id):
    """
    admin operation
    """
    return restaurants.Restaurant.init_request_create_update(app.current_request, restaurant_id).\
        endpoint_update()


@app.route('/restaurants/{restaurant_id}', methods=['DELETE'], authorizer=role_authorizer, cors=True)
def archive_restaurant(restaurant_id):
    """
    admin operation
    """
    return restaurants.Restaurant.init_request_create_update(
        app.current_request, restaurant_id=restaurant_id,
        special_body={'archived': True}
    ).endpoint_update()


# MENU ITEMS
@app.route('/menu-items/{restaurant_id}', methods=['GET'], cors=True)
def get_restaurant_menu(restaurant_id):
    return menu_items.MenuItem.endpoint_get_menu_items(app.current_request, restaurant_id=restaurant_id)


@app.route('/menu-items/{restaurant_id}', methods=['POST'], authorizer=role_authorizer, cors=True)
def create_menu_item(restaurant_id):
    """
    restaurant manager operation
    """
    return menu_items.MenuItem.init_request_create_update(app.current_request, restaurant_id=restaurant_id).\
        endpoint_create_menu_item()


@app.route('/menu-items/{restaurant_id}/{menu_item_id}', methods=['PUT'], authorizer=role_authorizer, cors=True)
def update_menu_item(restaurant_id, menu_item_id):
    """
    restaurant manager operation
    """
    return menu_items.MenuItem.init_request_create_update(
        app.current_request, restaurant_id=restaurant_id, menu_item_id=menu_item_id).endpoint_update_menu_item()


@app.route('/menu-items/{restaurant_id}/{menu_item_id}', methods=['DELETE'], authorizer=role_authorizer, cors=True)
def delete_menu_item(restaurant_id, menu_item_id):
    """
    restaurant manager operation
    """
    return menu_items.MenuItem.init_request_create_update(
        app.current_request, restaurant_id=restaurant_id,
        menu_item_id=menu_item_id, special_body={'archived': True}
    ).endpoint_update_menu_item()


# CART
@app.route('/carts', methods=['GET'], authorizer=role_authorizer, cors=True)
def get_cart():
    return carts.Cart.init_endpoint(app.current_request).endpoint_get_cart()


@app.route('/carts', methods=['POST'], authorizer=role_authorizer, cors=True)
def add_item_to_cart():
    return carts.Cart.init_endpoint(app.current_request).endpoint_add_item_to_cart()


@app.route('/carts/{menu_item_id}', methods=['DELETE'], authorizer=role_authorizer, cors=True)
def remove_item_from_cart(menu_item_id):
    return carts.Cart.init_endpoint(app.current_request).endpoint_remove_item_from_cart(menu_item_id)


@app.route('/carts', methods=['DELETE'], authorizer=role_authorizer, cors=True)
def clear_cart():
    return carts.Cart.init_endpoint(app.current_request).endpoint_clear_cart()


# ORDERS
@app.route('/orders', methods=['GET'], authorizer=role_authorizer, cors=True)
def get_orders():
    """
    user can get his orders
    restaurant manager don't have access
    admin don't have access
    """
    return orders.endpoint_get_orders(app.current_request)


@app.route('/orders/restaurant/{restaurant_id}', methods=['GET'], authorizer=role_authorizer, cors=True)
def get_restaurant_orders(restaurant_id):
    """
    restaurant manager can get restaurant's orders (he needs permissions to manage the restaurant)
    admin can get restaurant's orders by restaurant_id
    """
    return orders.endpoint_get_orders(app.current_request, 'restaurant', restaurant_id)


@app.route('/orders/user/{user_id}', methods=['GET'], authorizer=role_authorizer, cors=True)
def get_user_orders(user_id):
    """
    admin can get user's orders by user_id
    """
    return orders.endpoint_get_orders(app.current_request, 'user', user_id)


# Todo: TO BE IMPLEMENTED
@app.route('/orders/archived/{year_month}', methods=['GET'], authorizer=role_authorizer, cors=True)
def get_archived_orders(year_month):
    """
    user can get his orders
    restaurant manager can get restaurant's orders
    admin don't have access
    """
    return orders.get_archived_orders(app.current_request, year_month)


# Todo: TO BE IMPLEMENTED
@app.route('/orders/archived/restaurant/{restaurant_id}/{year_month}', methods=['GET'], authorizer=role_authorizer, cors=True)
def get_restaurant_archived_orders(restaurant_id, year_month):
    """
    admin can get restaurant's orders by restaurant_id
    """
    return orders.get_restaurant_archived_orders(app.current_request, restaurant_id, year_month)


# Todo: TO BE IMPLEMENTED
@app.route('/orders/archived/user/{user_id}/{year_month}', methods=['GET'], authorizer=role_authorizer, cors=True)
def get_user_archived_orders(user_id, year_month):
    """
    admin can get restaurant's orders by restaurant_id
    """
    return orders.get_user_archived_orders(app.current_request, user_id, year_month)


@app.route('/orders/id/{restaurant_id}/{order_id}', methods=['GET'], authorizer=role_authorizer, cors=True)
def get_order_by_id(order_id, restaurant_id):
    """
    user can get details only his orders
    restaurant manager can get details for any restaurant's orders
    admin can get details of any order
    """
    return orders.Order.init_request_get_order(app.current_request, order_id, restaurant_id).endpoint_get_by_id()


@app.route('/orders/id/unauthorized/{restaurant_id}/{order_id}', methods=['GET'], cors=True)
def get_order_by_id_unauthorized(restaurant_id, order_id):
    """
    Unauthorized user can get details of an order
    created by unauthorized user by ID
    Authorization is not needed
    """
    return orders.Order(id_=order_id, user_id=UNAUTHORIZED_USER, restaurant_id=restaurant_id).\
        endpoint_get_by_id()


@app.route('/orders/pre-order/unauthorized', methods=['POST'], cors=True)
def create_pre_order_unauthorized():
    """
    The endpoint is for creating pre-orders by unauthorized users
    Authorization is not needed
    """
    return orders.PreOrder.init_request_create_pre_order_unauthorized_user(app.current_request).\
        endpoint_create_pre_order()


@app.route('/orders/unauthorized', methods=['POST'], cors=True)
def create_order_unauthorized():
    """
    The endpoint is for creating orders by unauthorized users
    Authorization is not needed
    """
    return orders.Order.init_request_create_order_unauthorized(app.current_request).endpoint_create_order()


@app.route('/orders/pre-order', methods=['POST'], authorizer=role_authorizer, cors=True)
def create_pre_order_authorized():
    """
    The endpoint is for creating pre-orders by authorized users
    order details will be taken from user's cart
    """
    return orders.PreOrder.init_request_create_pre_order_authorized_user(app.current_request).\
        endpoint_create_pre_order()


@app.route('/orders', methods=['POST'], authorizer=role_authorizer, cors=True)
def create_order_authorized():
    """
    The endpoint is for creating orders by authorized users
    """
    return orders.Order.init_request_create_order_authorized(app.current_request).endpoint_create_order()


# Todo: TO BE IMPLEMENTED
@app.route('/orders/{restaurant_id}/{order_id}', methods=['PUT'], authorizer=role_authorizer, cors=True)
def update_order():
    """
    restaurant manager operation (comment required when manager updating an order)
    """
    return orders.update_order(app.current_request)


# Todo: TO BE IMPLEMENTED
@app.route('/orders/{restaurant_id}/{order_id}', methods=['DELETE'], authorizer=role_authorizer, cors=True)
def delete_order():
    """
    user can archive completed order
    restaurant manager can archive an order
    """
    return orders.delete_order(app.current_request)


# IMAGES
# Todo: TO BE IMPLEMENTED
@app.route('/image-upload', methods=['POST'], content_types=['multipart/form-data'], authorizer=role_authorizer, cors=True)
def image_upload():
    """
    restaurant manager operation
    """
    return images.image_upload(app.current_request)
