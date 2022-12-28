import json
from typing import List
from uuid import uuid4

import pytest

from chalicelib.constants import keys_structure
from chalicelib.utils import db
from test.utils.regression_test_data import get_company_admin_record, get_restaurant_manager_record, get_user_record
from test.utils.request_utils import make_request

from test.utils.fixtures import chalice_gateway

global company_id


def create_company_and_admin(request):
    global company_id
    # company_id = str(uuid4())
    company_id = 'f770d5f7-6dd2-4cdf-842b-5fd0dd84a52a'
    admin_record = get_company_admin_record(company_id)
    db.put_db_record(admin_record)

    def resource_teardown_admin_record():
        db.get_customers_table().delete_item(Key={'partkey': admin_record['partkey'], 'sortkey': admin_record['sortkey']})
    request.addfinalizer(resource_teardown_admin_record)

    return admin_record['id_']


def create_restaurant(chalice_gateway, request, id_admin, seq_number: int):
    global company_id
    rest_data = [
      {
        "address": "Time Square, New York, USA",
        "description": "Best restaurant in USA",
        "title": "MONSTER Time Square"
      },
      {
        "address": "Red Square, Moscow, Russia",
        "description": "First Moscow restaurant",
        "title": "Russian classic"
      },
      {
        "address": "Alexanderplatz, Berlin, Germany",
        "description": "Best German restaurant in Europe",
        "title": "Alexanderplatz first"
      }
    ]

    data = rest_data[seq_number]

    restaurant_to_create = {
        'title': data['title'],
        'address': data['address'],
        'description': data['description'],
        'cuisine': ['Chinese'],
        'settings': {
            "category_sequence": {
                1: "breakfast",
                2: "dinner",
                3: "pizza",
                4: "burgers"
            }
        },
        'opening_time': 10,
        'closing_time': 23
    }
    response = make_request(chalice_gateway, endpoint="/restaurants", method="POST",
                            json_body=restaurant_to_create, token=id_admin)
    id_ = json.loads(response["body"])["id"]

    def resource_teardown():
        db.get_customers_table().delete_item(Key={
            'partkey': keys_structure.restaurants_pk.format(company_id=company_id),
            'sortkey': keys_structure.restaurants_sk.format(restaurant_id=id_)
        })
    request.addfinalizer(resource_teardown)

    return id_


def create_restaurant_manager(request, restaurant_ids: list):
    global company_id
    rest_manager_record = get_restaurant_manager_record(company_id, restaurant_ids)
    db.put_db_record(rest_manager_record)

    def resource_teardown_admin_record():
        db.get_customers_table().delete_item(Key={'partkey': rest_manager_record['partkey'],
                                            'sortkey': rest_manager_record['sortkey']})

    request.addfinalizer(resource_teardown_admin_record)

    return rest_manager_record['id_']


def create_user(request):
    global company_id
    user_record = get_user_record(company_id)
    db.put_db_record(user_record)

    def resource_teardown_admin_record():
        db.get_customers_table().delete_item(Key={'partkey': user_record['partkey'], 'sortkey': user_record['sortkey']})

    request.addfinalizer(resource_teardown_admin_record)

    return user_record['id_']


def create_menu_item(chalice_gateway, request, restaurant_id, id_restaurant_manager, seq_number: int):
    global company_id
    menu_items_data = [
        {
            "title": "Cheeseburger",
            "description": "Best cheeseburger in the world",
            "category": "burgers",
            "price": 350
        },
        {
            "title": "Pepperoni",
            "description": "Classic pepperoni pizza",
            "category": "pizza",
            "price": 670
        },
        {
            "title": "Scrambled eggs",
            "description": "Classic breakfast scrambled eggs",
            "category": "breakfast",
            "price": 250
        },
        {
            "title": "Sausages breakfast",
            "description": "Classic sausage breakfast",
            "category": "breakfast",
            "price": 320
        },
        {
            "title": "Rib-eye steak",
            "description": "Classic Rib-eye steak",
            "category": "dinner",
            "price": 1300
        }
    ]

    data = menu_items_data[seq_number]
    menu_item_to_create = {
        'title': data['title'],
        'category': data['category'],
        'description': data['description'],
        'price': data['price']
    }
    response = make_request(chalice_gateway, endpoint=f"/menu-items/{restaurant_id}", method="POST",
                            json_body=menu_item_to_create, token=id_restaurant_manager)

    id_ = json.loads(response["body"])["id"]

    def resource_teardown_menu_item():
        db.get_customers_table().delete_item(Key={
            'partkey': keys_structure.menu_items_pk.format(company_id=company_id, restaurant_id=restaurant_id),
            'sortkey': keys_structure.menu_items_sk.format(menu_item_id=id_)
        })
    request.addfinalizer(resource_teardown_menu_item)

    return id_


def add_item_to_cart(chalice_gateway, request, id_user, restaurant_id, menu_items: List[List]):
    global company_id
    for item in menu_items:
        req_body = {
            'menu_item_id': item[0],
            'qty': item[1]
        }
        response = make_request(chalice_gateway, endpoint=f"/carts/{restaurant_id}",
                                json_body=req_body, method="POST", token=id_user)
        assert response['statusCode'] == 200

    def resource_teardown_cart():
        db.get_customers_table().delete_item(Key={
            'partkey': keys_structure.carts_pk.format(company_id=company_id, restaurant_id=restaurant_id),
            'sortkey': keys_structure.carts_sk.format(user_id=id_user)
        })
    request.addfinalizer(resource_teardown_cart)


def create_pre_order_authorized_user(chalice_gateway, request, id_user, restaurant_id, user_number):
    global company_id
    request_body = [
        {
            'user_phone_number': '+79216146600',
            'user_email': 'rachko.a@gmail.com',
            'delivery_address': 'Mayskiy lane, 2, flat 119',
            'comment': 'Please deliver my order ASAP',
            'payment_method': 'cash',
            'delivery_method': 'delivery'
        },
        {
            'user_phone_number': '+79216065856',
            'user_email': 'maxbelogurov@gmail.com',
            'delivery_address': 'Sovetskiy av., 75',
            'comment': 'Hope for the best',
            'payment_method': 'card',
            'delivery_method': 'delivery'
        },
    ]
    response = make_request(chalice_gateway, endpoint=f"/orders/pre-order/{restaurant_id}",
                            json_body=request_body[user_number], token=id_user, method="POST")

    id_ = json.loads(response["body"])['id']

    def resource_teardown_pre_order():
        db.get_customers_table().delete_item(Key={
            'partkey': keys_structure.pre_orders_pk.format(company_id=company_id, user_id=id_user),
            'sortkey': keys_structure.pre_orders_sk.format(order_id=id_)
        })
    request.addfinalizer(resource_teardown_pre_order)

    return id_


def create_order_authorized_user(chalice_gateway, request, pre_order_id, id_user, restaurant_id):
    global company_id
    response = make_request(chalice_gateway, endpoint=f"/orders", token=id_user,
                            json_body={'pre_order_id': pre_order_id}, method="POST")

    id_ = json.loads(response["body"])['id']

    def resource_teardown_order():
        db.get_customers_table().delete_item(Key={
            'partkey': keys_structure.orders_pk.format(company_id=company_id),
            'sortkey': keys_structure.orders_sk.format(restaurant_id=restaurant_id, order_id=id_)
        })
    request.addfinalizer(resource_teardown_order)

    return id_


def create_orders(chalice_gateway, request, menu_items, restaurant_1_id,
                  restaurant_2_id, restaurant_3_id, user_1_id, user_2_id):
    orders = {
        1: {
            'items': [[menu_items[0], 1], [menu_items[1], 2]],
            'restaurant_id': restaurant_1_id
        },
        2: {
            'items': [[menu_items[3], 3], [menu_items[4], 1]],
            'restaurant_id': restaurant_3_id
        },
        3: {
            'items': [[menu_items[2], 3]],
            'restaurant_id': restaurant_2_id
        },
        4: {
            'items': [[menu_items[1], 3], [menu_items[0], 2]],
            'restaurant_id': restaurant_1_id
        },
        5: {
            'items': [[menu_items[1], 4]],
            'restaurant_id': restaurant_1_id
        },
        6: {
            'items': [[menu_items[2], 1]],
            'restaurant_id': restaurant_2_id
        },

    }
    add_item_to_cart(chalice_gateway, request, user_1_id, orders[1]['restaurant_id'], orders[1]['items'])
    add_item_to_cart(chalice_gateway, request, user_2_id, orders[2]['restaurant_id'], orders[2]['items'])

    pre_order_id_1 = create_pre_order_authorized_user(
        chalice_gateway, request, user_1_id, orders[1]['restaurant_id'], 0)
    pre_order_id_2 = create_pre_order_authorized_user(
        chalice_gateway, request, user_2_id, orders[2]['restaurant_id'], 1)

    order_id_1 = create_order_authorized_user(chalice_gateway, request, pre_order_id_1, user_1_id, restaurant_1_id)
    order_id_2 = create_order_authorized_user(chalice_gateway, request, pre_order_id_2, user_2_id, restaurant_3_id)
    orders[1]['id'] = order_id_1
    orders[2]['id'] = order_id_2

    add_item_to_cart(chalice_gateway, request, user_1_id, orders[3]['restaurant_id'], orders[3]['items'])
    add_item_to_cart(chalice_gateway, request, user_2_id, orders[4]['restaurant_id'], orders[4]['items'])

    pre_order_id_3 = create_pre_order_authorized_user(
        chalice_gateway, request, user_1_id, orders[3]['restaurant_id'], 0)
    pre_order_id_4 = create_pre_order_authorized_user(
        chalice_gateway, request, user_2_id, orders[4]['restaurant_id'], 1)

    order_id_3 = create_order_authorized_user(chalice_gateway, request, pre_order_id_3, user_1_id, restaurant_2_id)
    order_id_4 = create_order_authorized_user(chalice_gateway, request, pre_order_id_4, user_2_id, restaurant_1_id)
    orders[3]['id'] = order_id_3
    orders[4]['id'] = order_id_4

    add_item_to_cart(chalice_gateway, request, user_1_id, orders[5]['restaurant_id'], orders[5]['items'])
    pre_order_id_5 = create_pre_order_authorized_user(
        chalice_gateway, request, user_1_id, orders[5]['restaurant_id'], 0)
    order_id_5 = create_order_authorized_user(chalice_gateway, request, pre_order_id_5, user_1_id, restaurant_1_id)
    orders[5]['id'] = order_id_5

    add_item_to_cart(chalice_gateway, request, user_1_id, orders[6]['restaurant_id'], orders[6]['items'])
    pre_order_id_6 = create_pre_order_authorized_user(
        chalice_gateway, request, user_1_id, orders[6]['restaurant_id'], 0)
    order_id_6 = create_order_authorized_user(chalice_gateway, request, pre_order_id_6, user_1_id, restaurant_2_id)
    orders[6]['id'] = order_id_6

    return orders


def assert_user_orders(list_of_ids_to_check, orders, orders_response_body, user_id, restaurant_id=None):
    for order in orders_response_body:
        order_id = order['id']
        order_source = [order_source for order_source in orders.values() if order_source['id'] == order_id][0]
        item_ids_source = sorted([item[0] for item in order_source['items']])
        item_ids_response = sorted([item for item in order['menu_items'].keys()])
        assert item_ids_response == item_ids_source

        item_qty_source = sorted([item[1] for item in order_source['items']])
        item_qty_response = sorted([item['qty'] for item in order['menu_items'].values()])
        assert item_qty_source == item_qty_response

        assert order['user_id'] == user_id
        assert order_id in list_of_ids_to_check
        assert order['amount'] == sum([item['details']['price'] * item['qty'] for item in order['menu_items'].values()])
        if restaurant_id is not None:
            assert order['restaurant_id'] == restaurant_id


def assert_restaurant_orders(list_of_ids_to_check, orders, orders_response_body, restaurant_id):
    for order in orders_response_body:
        order_id = order['id']
        order_source = [order_source for order_source in orders.values() if order_source['id'] == order_id][0]
        item_ids_source = sorted([item[0] for item in order_source['items']])
        item_ids_response = sorted([item for item in order['menu_items'].keys()])
        assert item_ids_response == item_ids_source

        item_qty_source = sorted([item[1] for item in order_source['items']])
        item_qty_response = sorted([item['qty'] for item in order['menu_items'].values()])
        assert item_qty_source == item_qty_response

        assert order['restaurant_id'] == restaurant_id
        assert order_id in list_of_ids_to_check
        assert order['amount'] == sum([item['details']['price'] * item['qty'] for item in order['menu_items'].values()])


@pytest.mark.local_db_test
def test_regression(chalice_gateway, request):
    id_admin = create_company_and_admin(request)

    restaurant_1_id, restaurant_2_id, restaurant_3_id = [
        create_restaurant(chalice_gateway, request, id_admin, seq_number=number) for number in range(3)
    ]

    restaurant_manager_1_id = create_restaurant_manager(request, [restaurant_1_id, restaurant_2_id])
    restaurant_manager_2_id = create_restaurant_manager(request, [restaurant_3_id])

    user_1_id, user_2_id = [create_user(request) for _ in range(2)]

    menu_items = [
        create_menu_item(chalice_gateway, request, restaurant_1_id, restaurant_manager_1_id, 0),
        create_menu_item(chalice_gateway, request, restaurant_1_id, restaurant_manager_2_id, 1),
        create_menu_item(chalice_gateway, request, restaurant_2_id, restaurant_manager_2_id, 2),
        create_menu_item(chalice_gateway, request, restaurant_3_id, restaurant_manager_2_id, 3),
        create_menu_item(chalice_gateway, request, restaurant_3_id, restaurant_manager_1_id, 4)
        ]

    orders = create_orders(chalice_gateway, request, menu_items, restaurant_1_id,
                           restaurant_2_id, restaurant_3_id, user_1_id, user_2_id)
    # Get orders by first users
    orders_user_1_response = make_request(chalice_gateway, endpoint=f'/orders', token=user_1_id, method="GET")
    # Get orders by first user (restaurant specified)
    orders_user_1_rest_1_resp = make_request(
        chalice_gateway, endpoint=f'/orders?restaurant_id={restaurant_1_id}', token=user_1_id, method="GET")
    # Get orders by second user
    orders_user_2_response = make_request(chalice_gateway, endpoint='/orders', token=user_2_id, method="GET")

    orders_user_1_body = json.loads(orders_user_1_response["body"])
    orders_user_1_rest_1_body = json.loads(orders_user_1_rest_1_resp["body"])
    orders_user_2_body = json.loads(orders_user_2_response["body"])

    assert all([
        orders_user_1_body['last_evaluated_key'] is None,
        orders_user_1_rest_1_body['last_evaluated_key'] is None,
        orders_user_2_body['last_evaluated_key'] is None
    ])

    assert len(orders_user_1_body['orders']) == 4
    assert len(orders_user_1_rest_1_body['orders']) == 2
    assert len(orders_user_2_body['orders']) == 2

    # Assert first user all orders
    assert_user_orders([orders[1]['id'], orders[3]['id'], orders[5]['id'], orders[6]['id']],
                       orders, orders_user_1_body['orders'], user_1_id)
    # Assert first user orders from specified restaurant
    assert_user_orders([orders[1]['id'], orders[5]['id']], orders, orders_user_1_rest_1_body['orders'],
                       user_1_id, restaurant_id=restaurant_1_id)
    # Assert second user all orders
    assert_user_orders([orders[2]['id'], orders[4]['id']], orders, orders_user_2_body['orders'], user_2_id)

    # Get first restaurant orders by first restaurant manager
    orders_restaurant_1_response = make_request(chalice_gateway, endpoint=f'/orders/restaurant/{restaurant_1_id}',
                                                token=restaurant_manager_1_id, method="GET")
    # Get second restaurant orders by first restaurant manager
    orders_restaurant_2_response = make_request(chalice_gateway, endpoint=f'/orders/restaurant/{restaurant_2_id}',
                                                token=restaurant_manager_1_id, method="GET")
    # Get third restaurant orders by second restaurant manager
    orders_restaurant_3_response = make_request(chalice_gateway, endpoint=f'/orders/restaurant/{restaurant_3_id}',
                                                token=restaurant_manager_2_id, method="GET")

    orders_restaurant_1_body = json.loads(orders_restaurant_1_response["body"])
    orders_restaurant_2_body = json.loads(orders_restaurant_2_response["body"])
    orders_restaurant_3_body = json.loads(orders_restaurant_3_response["body"])
    assert all([
        orders_restaurant_1_body['last_evaluated_key'] is None,
        orders_restaurant_2_body['last_evaluated_key'] is None,
        orders_restaurant_3_body['last_evaluated_key'] is None
    ])

    # Assert first restaurant orders got by first restaurant manager
    assert_restaurant_orders([orders[1]['id'], orders[4]['id'], orders[5]['id']],
                             orders, orders_restaurant_1_body['orders'], restaurant_1_id)
    # Assert second restaurant orders got by first restaurant manager
    assert_restaurant_orders([orders[3]['id'], orders[6]['id']],
                             orders, orders_restaurant_2_body['orders'], restaurant_2_id)
    # Assert third restaurant orders got by second restaurant manager
    assert_restaurant_orders([orders[2]['id']], orders, orders_restaurant_3_body['orders'], restaurant_3_id)

    # Test page_size query parameter
    orders_restaurant_1_limited_response = make_request(
        chalice_gateway,
        endpoint=f'/orders/restaurant/{restaurant_1_id}?page_size=2',
        token=restaurant_manager_1_id,
        method="GET"
    )
    orders_restaurant_1_limited_body = json.loads(orders_restaurant_1_limited_response["body"])
    assert len(orders_restaurant_1_limited_body['orders']) == 2
    last_key = orders_restaurant_1_limited_body['last_evaluated_key']
    assert last_key is not None

    # Test start_key parameter
    orders_restaurant_1_from_key_response = make_request(
        chalice_gateway,
        endpoint=f'/orders/restaurant/{restaurant_1_id}?start_key={last_key}',
        token=restaurant_manager_1_id,
        method="GET"
    )
    orders_restaurant_1_from_key_body = json.loads(orders_restaurant_1_from_key_response["body"])
    assert len(orders_restaurant_1_from_key_body['orders']) == 1
    assert sorted(
        [order['id'] for order in orders_restaurant_1_body['orders']]
    ) == sorted(
        [order['id'] for order in [*orders_restaurant_1_from_key_body['orders'],
                                   *orders_restaurant_1_limited_body['orders']]]
    )

    # Test permissions error
    orders_restaurant_error_response = make_request(
        chalice_gateway, endpoint=f'/orders/restaurant/{restaurant_2_id}', token=restaurant_manager_2_id, method="GET")
    error_response_body = json.loads(orders_restaurant_error_response['body'])
    assert error_response_body['error'] == 'Access Denied error'
    assert error_response_body['exception'] == 'AccessDenied'
    assert error_response_body['message'] == "You don't have permissions to access this restaurant"
