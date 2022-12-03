from chalice import Chalice

from chalicelib import auth, orders, carts, menu_items, restaurants, images

app = Chalice(app_name='restaurant-menu-and-order')


@app.authorizer()
def test_auth(auth_request):
    return auth.test_auth(auth_request)


@app.route('/health-check', authorizer=test_auth)
def health_check():
    return {'health': 'check'}


@app.route('/users', methods=['POST'], cors=True)
def create_user():
    user_as_json = app.current_request.json_body
    return {'user': user_as_json}


# RESTAURANTS
@app.route('/restaurants', methods=['GET'], cors=True)
def get_restaurants():
    return restaurants.Restaurant.endpoint_get_restaurants(app.current_request)


@app.route('/restaurants/{restaurant_id}', methods=['GET'], authorizer=test_auth, cors=True)
def get_restaurant_by_id(restaurant_id):
    return restaurants.Restaurant.init_request_get_by_id(app.current_request, restaurant_id).\
        endpoint_get_restaurant_by_id()


@app.route('/restaurants/{restaurant_id}/delivery-price/{address}', methods=['GET'], cors=True)
def get_delivery_address(restaurant_id, address):
    return restaurants.Restaurant.init_request_get_by_id(app.current_request, restaurant_id).\
        endpoint_get_delivery_price(address)


@app.route('/restaurants', methods=['POST'], authorizer=test_auth, cors=True)
def create_restaurant():
    """
    admin operation
    """
    return restaurants.Restaurant.init_request_create_update(app.current_request).endpoint_create_restaurant()


@app.route('/restaurants/{restaurant_id}', methods=['PUT'], cors=True)
def update_restaurant(restaurant_id):
    """
    admin operation
    """
    return restaurants.Restaurant.init_request_create_update(app.current_request, restaurant_id).\
        endpoint_update_restaurant()


@app.route('/restaurants/{restaurant_id}', methods=['DELETE'], cors=True)
def archive_restaurant(restaurant_id):
    """
    admin operation
    """
    return restaurants.Restaurant.init_request_create_update(
        app.current_request, restaurant_id=restaurant_id,
        special_body={'archived': True}
    ).endpoint_update_restaurant()


# MENU ITEMS
@app.route('/menu-items/{restaurant_id}', methods=['GET'], cors=True)
def get_restaurant_menu(restaurant_id):
    return menu_items.MenuItem.endpoint_get_menu_items(app.current_request, restaurant_id=restaurant_id)


@app.route('/menu-items/{restaurant_id}', methods=['POST'], cors=True)
def create_menu_item(restaurant_id):
    """
    restaurant manager operation
    """
    return menu_items.MenuItem.init_request_create_update(app.current_request, restaurant_id=restaurant_id).\
        endpoint_create_menu_item()


@app.route('/menu-items/{restaurant_id}/{menu_item_id}', methods=['PUT'], cors=True)
def update_menu_item(restaurant_id, menu_item_id):
    """
    restaurant manager operation
    """
    return menu_items.MenuItem.init_request_create_update(
        app.current_request, restaurant_id=restaurant_id, menu_item_id=menu_item_id).endpoint_update_menu_item()


@app.route('/menu-items/{restaurant_id}/{menu_item_id}', methods=['DELETE'], cors=True)
def delete_menu_item(restaurant_id, menu_item_id):
    """
    restaurant manager operation
    """
    return menu_items.MenuItem.init_request_create_update(
        app.current_request, restaurant_id=restaurant_id,
        menu_item_id=menu_item_id, special_body={'archived': True}
    ).endpoint_update_menu_item()


# CART
@app.route('/carts', methods=['GET'], cors=True)
def get_cart():
    return carts.Cart.init_endpoint(app.current_request).endpoint_get_cart()


@app.route('/carts/{restaurant_id}/{menu_item_id}', methods=['POST'], cors=True)
def add_item_to_cart(restaurant_id, menu_item_id):
    return carts.Cart.init_endpoint(app.current_request).endpoint_add_item_to_cart(restaurant_id, menu_item_id)


@app.route('/carts/{menu_item_id}', methods=['DELETE'], cors=True)
def remove_item_from_cart(menu_item_id):
    return carts.Cart.init_endpoint(app.current_request).endpoint_remove_item_from_cart(menu_item_id)


@app.route('/carts', methods=['DELETE'], cors=True)
def clear_cart():
    return carts.Cart.init_endpoint(app.current_request).endpoint_clear_cart()


# ORDERS
@app.route('/orders', methods=['GET'], cors=True)
def get_orders():
    """
    user can get his orders
    restaurant manager can get restaurant's orders
    admin don't have access
    """
    return orders.get_orders(app.current_request)


@app.route('/orders/restaurant/{restaurant_id}', methods=['GET'], cors=True)
def get_restaurant_orders(restaurant_id):
    """
    admin can get restaurant's orders by restaurant_id
    """
    return orders.get_restaurant_orders(app.current_request, restaurant_id)


@app.route('/orders/user/{user_id}', methods=['GET'], cors=True)
def get_restaurant_orders(restaurant_id):
    """
    admin can get restaurant's orders by restaurant_id
    """
    return orders.get_user_orders(app.current_request, restaurant_id)


@app.route('/orders/archived/{year_month}', methods=['GET'], cors=True)
def get_archived_orders(year_month):
    """
    user can get his orders
    restaurant manager can get restaurant's orders
    admin don't have access
    """
    return orders.get_archived_orders(app.current_request, year_month)


@app.route('/orders/archived/restaurant/{restaurant_id}/{year_month}', methods=['GET'], cors=True)
def get_restaurant_archived_orders(restaurant_id, year_month):
    """
    admin can get restaurant's orders by restaurant_id
    """
    return orders.get_restaurant_archived_orders(app.current_request, restaurant_id, year_month)


@app.route('/orders/archived/user/{user_id}/{year_month}', methods=['GET'], cors=True)
def get_user_archived_orders(user_id, year_month):
    """
    admin can get restaurant's orders by restaurant_id
    """
    return orders.get_user_archived_orders(app.current_request, user_id, year_month)


@app.route('/orders/{order_id}', methods=['GET'], cors=True)
def get_order_by_id(order_id):
    """
    user can get details only his orders
    restaurant manager can get details for any restaurant's orders
    admin can get details of any order
    """
    return orders.get_order_by_id(app.current_request, order_id)


@app.route('/orders/unauthorized/{order_id}', methods=['GET'], cors=True)
def get_order_by_id_unauthorized(order_id):
    """
    user can get details only his orders
    restaurant manager can get details for any restaurant's orders
    admin can get details of any order
    """
    return orders.Order.init_request_get_by_id_unauthorized_user(app.current_request, order_id).\
        endpoint_get_by_id_unauthorized_user()


@app.route('/orders/pre-order/unauthorized', methods=['POST'], cors=True)
def create_pre_order_unauthorized():
    """
    The endpoint is for creating pre-orders by unauthorized users
    Doesn't have authorization
    """
    return orders.PreOrder.init_request_create_pre_order_unauthorized_user(app.current_request).\
        endpoint_create_pre_order_unauthorized_user()


@app.route('/orders/unauthorized', methods=['POST'], cors=True)
def create_order_unauthorized():
    """
    The endpoint is for creating orders by unauthorized users
    Doesn't have authorization
    """
    return orders.Order.init_request_create_order_unauthorized_user(app.current_request).\
        endpoint_create_order_unauthorized_user()


@app.route('/orders/pre-order', methods=['POST'], cors=True)
def create_pre_order_unauthorized():
    """
    The endpoint is for creating pre-orders by authorized users
    Doesn't have authorization
    """
    return orders.PreOrder.init_request_create_pre_order_unauthorized_user(app.current_request).\
        endpoint_create_pre_order_authorized_user()


@app.route('/orders', methods=['POST'], cors=True)
def create_order_unauthorized():
    """
    The endpoint is for creating orders by authorized users
    Doesn't have authorization
    """
    return orders.Order.init_request_create_order_unauthorized_user(app.current_request).\
        endpoint_create_order_authorized_user()


@app.route('/orders/{order_id}', methods=['PUT'], cors=True)
def update_order():
    """
    restaurant manager operation (comment required)
    """
    return orders.update_order(app.current_request)


@app.route('/orders/{order_id}', methods=['DELETE'], cors=True)
def delete_order():
    """
    user can archive completed order
    restaurant manager can archive an order
    """
    return orders.delete_order(app.current_request)


# IMAGES
@app.route('/image-upload/{entity_type}/{entity_id}', methods=['POST'], cors=True)
def image_upload(entity_type, entity_id):
    """
    restaurant manager operation
    """
    return images.image_upload(app.current_request, entity_type, entity_id)

