import json
from decimal import Decimal

import pytest as pytest

from chalicelib.constants import keys_structure
from chalicelib.constants.constants import UNAUTHORIZED_USER
from chalicelib.constants.status_codes import http200
from chalicelib.utils import db
from test.utils.request_utils import make_request

from test.utils.fixtures import chalice_gateway

token_admin = 'admin'
token_restaurant_manager = 'restaurant_manager'
token_user = 'user'

id_admin = '13303309-d941-486f-b600-3e90929ac50f'
id_restaurant_manager = '8178f948-cdc2-4e8c-b013-07a956e7e72a'
id_user = 'e5b01491-e538-4be3-8d3c-a57db7fc43c1'


def create_test_restaurant(chalice_gateway, request):
    restaurant_to_create = {
        'title': 'test restaurant title',
        'address': 'Time Square, New York',
        'description': "This is my test restaurant",
        'cuisine': ['Chinese'],
        'opening_time': 10,
        'closing_time': 23
    }
    response = make_request(chalice_gateway, endpoint="/restaurants", method="POST",
                            json_body=restaurant_to_create, token=id_admin)

    id_ = json.loads(response["body"])["id"]

    def resource_teardown_rest():
        db.get_gen_table().delete_item(Key={
            'partkey': keys_structure.restaurants_pk,
            'sortkey': keys_structure.restaurants_sk.format(restaurant_id=id_)
        })
    request.addfinalizer(resource_teardown_rest)

    return id_


def create_test_menu_items(chalice_gateway, restaurant_id, request):
    menu_item_to_create = {
        'title': 'Scrambled eggs',
        'category': 'breakfast',
        'description': 'Eggs especially for breakfast',
        'price': 9.99
    }
    menu_item_to_create_2 = {
        'title': 'Burger',
        'category': 'Dinner',
        'description': 'The best Burger in the world',
        'price': 18.50
    }
    response = make_request(chalice_gateway, endpoint=f"/menu-items/{restaurant_id}", method="POST",
                            json_body=menu_item_to_create, token=id_restaurant_manager)

    response_2 = make_request(chalice_gateway, endpoint=f"/menu-items/{restaurant_id}", method="POST",
                              json_body=menu_item_to_create_2, token=id_restaurant_manager)

    id_ = json.loads(response["body"])["id"]
    id_2 = json.loads(response_2["body"])["id"]

    def resource_teardown_menu_items():
        db.get_gen_table().delete_item(Key={
            'partkey': keys_structure.menu_items_pk.format(restaurant_id=restaurant_id),
            'sortkey': keys_structure.menu_items_sk.format(menu_item_id=id_)
        })
        db.get_gen_table().delete_item(Key={
            'partkey': keys_structure.menu_items_pk.format(restaurant_id=restaurant_id),
            'sortkey': keys_structure.menu_items_sk.format(menu_item_id=id_2)
        })
    request.addfinalizer(resource_teardown_menu_items)

    return id_, id_2


def add_test_items_to_cart(chalice_gateway, restaurant_id, item_ids: list, request):

    for item_id in item_ids:
        response = make_request(chalice_gateway, endpoint=f"/carts/{restaurant_id}/{item_id}",
                                method="POST", token=id_user)
        assert response['statusCode'] == 200

    def resource_teardown_menu_items():
        db.get_gen_table().delete_item(Key={
            'partkey': keys_structure.carts_pk,
            'sortkey': keys_structure.carts_sk.format(user_id=id_user)
        })
    request.addfinalizer(resource_teardown_menu_items)


def create_test_pre_order_unauthorized_user(chalice_gateway, restaurant_id, menu_item_to_order_1, menu_item_to_order_2, request):
    order_data = {
        'user_phone_number': '+79216146600',
        'user_email': 'rachko.a@gmail.com',
        'restaurant_id': restaurant_id,
        'delivery_address': 'Mayskiy lane, 2, flat 119',
        'item_ids': [menu_item_to_order_1, menu_item_to_order_2],
        'comment': 'Please deliver my order ASAP'
    }

    response = make_request(chalice_gateway, endpoint=f"/orders/pre-order/unauthorized",
                            method="POST", json_body=order_data)

    response_body = json.loads(response["body"])
    id_ = response_body['id']

    def resource_teardown_pre_order():
        db.get_gen_table().delete_item(Key={
            'partkey': keys_structure.pre_orders_pk.format(user_id=UNAUTHORIZED_USER),
            'sortkey': keys_structure.pre_orders_sk.format(order_id=id_)
        })
    request.addfinalizer(resource_teardown_pre_order)

    return id_


def create_test_order_unauthorized_user(chalice_gateway, pre_order_id, restaurant_id, request):
    response = make_request(chalice_gateway, endpoint=f"/orders/unauthorized", method="POST",
                            json_body={'pre_order_id': pre_order_id})

    id_ = json.loads(response["body"])['id']

    def resource_teardown_order():
        db.get_gen_table().delete_item(Key={
            'partkey': keys_structure.orders_pk.format(restaurant_id=restaurant_id),
            'sortkey': keys_structure.orders_sk.format(user_id=UNAUTHORIZED_USER, order_id=id_)
        })
    request.addfinalizer(resource_teardown_order)

    return id_


def create_test_pre_order_authorized_user(chalice_gateway, request):
    request_body = {
        'user_phone_number': '+79216146600',
        'user_email': 'rachko.a@gmail.com',
        'delivery_address': 'Mayskiy lane, 2, flat 119',
        'comment': 'Please deliver my order ASAP'
    }

    response = make_request(chalice_gateway, endpoint=f"/orders/pre-order", json_body=request_body,
                            token=id_user, method="POST")

    id_ = json.loads(response["body"])['id']

    def resource_teardown_pre_order():
        db.get_gen_table().delete_item(Key={
            'partkey': keys_structure.pre_orders_pk.format(user_id=id_user),
            'sortkey': keys_structure.pre_orders_sk.format(order_id=id_)
        })
    request.addfinalizer(resource_teardown_pre_order)

    return id_


def create_test_order_authorized_user(chalice_gateway, pre_order_id, restaurant_id, request):
    response = make_request(chalice_gateway, endpoint=f"/orders", token=id_user,
                            json_body={'pre_order_id': pre_order_id}, method="POST")

    id_ = json.loads(response["body"])['id']

    def resource_teardown_order():
        db.get_gen_table().delete_item(Key={
            'partkey': keys_structure.orders_pk.format(restaurant_id=restaurant_id),
            'sortkey': keys_structure.orders_sk.format(user_id=id_user, order_id=id_)
        })
    request.addfinalizer(resource_teardown_order)

    return id_


@pytest.mark.local_db_test
def test_create_pre_order_unauthorized_user(chalice_gateway, request):
    restaurant_id = create_test_restaurant(chalice_gateway, request)
    menu_item_id, menu_item_id_2 = create_test_menu_items(chalice_gateway, restaurant_id, request)

    order_data = {
        'user_phone_number': '+79216146600',
        'user_email': 'rachko.a@gmail.com',
        'restaurant_id': restaurant_id,
        'delivery_address': 'Mayskiy lane, 2, flat 119',
        'item_ids': [menu_item_id, menu_item_id_2],
        'comment': 'Please deliver my order ASAP'
    }

    response = make_request(chalice_gateway, endpoint=f"/orders/pre-order/unauthorized",
                            method="POST", json_body=order_data)

    response_body = json.loads(response["body"])
    order_id = response_body['id']

    pre_order_pk = keys_structure.pre_orders_pk.format(user_id='unauthorized_user')
    pre_order_sk = keys_structure.pre_orders_sk.format(order_id=order_id)

    def resource_teardown():
        db.get_gen_table().delete_item(Key={'partkey': pre_order_pk, 'sortkey': pre_order_sk})
    request.addfinalizer(resource_teardown)

    assert response['statusCode'] == http200, f"status code not as expected"

    assert response_body['user_id'] == 'unauthorized_user'
    assert response_body['user_phone_number'] == '+79216146600'
    assert response_body['user_email'] == 'rachko.a@gmail.com'
    assert response_body['restaurant_id'] == restaurant_id
    assert response_body['delivery_address'] == 'Mayskiy lane, 2, flat 119'
    assert len(response_body['item_ids']) == 2
    assert response_body['amount'] == 28.49
    assert response_body['archived'] is False
    assert response_body['comment'] == 'Please deliver my order ASAP'

    db_record = db.get_gen_table().get_item(Key={'partkey': pre_order_pk, 'sortkey': pre_order_sk})['Item']

    assert db_record['archived'] is False


@pytest.mark.local_db_test
def test_create_order_unauthorized_user(chalice_gateway, request):
    restaurant_id = create_test_restaurant(chalice_gateway, request)
    menu_item_id, menu_item_id_2 = create_test_menu_items(chalice_gateway, restaurant_id, request)
    pre_order_id = create_test_pre_order_unauthorized_user(chalice_gateway, restaurant_id, menu_item_id,
                                                           menu_item_id_2, request)

    response = make_request(chalice_gateway, endpoint=f"/orders/unauthorized",
                            json_body={'pre_order_id': pre_order_id}, method="POST")

    response_body = json.loads(response["body"])
    order_id = response_body['id']

    order_pk = keys_structure.orders_pk.format(restaurant_id=restaurant_id)
    order_sk = keys_structure.orders_sk.format(user_id=UNAUTHORIZED_USER, order_id=order_id)

    def resource_teardown():
        db.get_gen_table().delete_item(Key={'partkey': order_pk, 'sortkey': order_sk})
    request.addfinalizer(resource_teardown)

    assert response['statusCode'] == http200, f"status code not as expected"

    assert response_body['user_id'] == 'unauthorized_user'
    assert response_body['user_phone_number'] == '+79216146600'
    assert response_body['user_email'] == 'rachko.a@gmail.com'
    assert response_body['restaurant_id'] == restaurant_id
    assert response_body['delivery_address'] == 'Mayskiy lane, 2, flat 119'
    assert len(response_body['item_ids']) == 2
    assert response_body['amount'] == 28.49
    assert response_body['paid'] is False
    assert response_body['history'] == ['created']
    assert response_body['archived'] is False
    assert response_body['comment'] == 'Please deliver my order ASAP'
    assert response_body['feedback'] is None

    db_record = db.get_gen_table().get_item(Key={'partkey': order_pk, 'sortkey': order_sk})['Item']

    assert db_record['archived'] is False


@pytest.mark.local_db_test
def test_get_order_by_id_unauthorized_user(chalice_gateway, request):
    restaurant_id = create_test_restaurant(chalice_gateway, request)
    menu_item_id, menu_item_id_2 = create_test_menu_items(chalice_gateway, restaurant_id, request)
    pre_order_id = create_test_pre_order_unauthorized_user(chalice_gateway, restaurant_id, menu_item_id,
                                                           menu_item_id_2, request)
    order_id = create_test_order_unauthorized_user(chalice_gateway, pre_order_id, restaurant_id, request)

    response = make_request(chalice_gateway, endpoint=f"/orders/id/unauthorized/{restaurant_id}/{order_id}",
                            method="GET")

    response_body = json.loads(response["body"])

    assert response['statusCode'] == http200, f"status code not as expected"

    assert response_body['id'] == order_id
    assert response_body['user_id'] == 'unauthorized_user'
    assert response_body['user_phone_number'] == '+79216146600'
    assert response_body['user_email'] == 'rachko.a@gmail.com'
    assert response_body['restaurant_id'] == restaurant_id
    assert response_body['delivery_address'] == 'Mayskiy lane, 2, flat 119'
    assert len(response_body['item_ids']) == 2
    assert response_body['amount'] == 28.49
    assert response_body['paid'] is False
    assert response_body['history'] == ['created']
    assert response_body['archived'] is False
    assert response_body['comment'] == 'Please deliver my order ASAP'
    assert response_body['feedback'] is None


@pytest.mark.local_db_test
def test_create_pre_order_authorized_user(chalice_gateway, request):
    restaurant_id = create_test_restaurant(chalice_gateway, request)
    menu_item_id, menu_item_id_2 = create_test_menu_items(chalice_gateway, restaurant_id, request)
    add_test_items_to_cart(chalice_gateway, restaurant_id, [menu_item_id, menu_item_id_2], request)

    request_body = {
        'user_phone_number': '+79216146600',
        'user_email': 'rachko.a@gmail.com',
        'delivery_address': 'Mayskiy lane, 2, flat 119',
        'comment': 'Please deliver my order ASAP'
    }

    response = make_request(chalice_gateway, endpoint=f"/orders/pre-order", json_body=request_body,
                            token=id_user, method="POST")

    response_body = json.loads(response["body"])
    pre_order_id = response_body['id']

    pre_order_pk = keys_structure.pre_orders_pk.format(user_id=id_user)
    pre_order_sk = keys_structure.pre_orders_sk.format(order_id=pre_order_id)

    def resource_teardown():
        db.get_gen_table().delete_item(Key={'partkey': pre_order_pk, 'sortkey': pre_order_sk})
    request.addfinalizer(resource_teardown)

    assert response_body['user_id'] == id_user
    assert response_body['user_phone_number'] == '+79216146600'
    assert response_body['user_email'] == 'rachko.a@gmail.com'
    assert response_body['restaurant_id'] == restaurant_id
    assert response_body['delivery_address'] == 'Mayskiy lane, 2, flat 119'
    assert len(response_body['item_ids']) == 2
    assert response_body['amount'] == 28.49
    assert response_body['comment'] == 'Please deliver my order ASAP'


@pytest.mark.local_db_test
def test_create_order_authorized_user(chalice_gateway, request):
    restaurant_id = create_test_restaurant(chalice_gateway, request)
    menu_item_id, menu_item_id_2 = create_test_menu_items(chalice_gateway, restaurant_id, request)
    add_test_items_to_cart(chalice_gateway, restaurant_id, [menu_item_id, menu_item_id_2], request)
    pre_order_id = create_test_pre_order_authorized_user(chalice_gateway, request)

    response = make_request(chalice_gateway, endpoint=f"/orders", json_body={'pre_order_id': pre_order_id},
                            token=id_user, method="POST")

    response_body = json.loads(response["body"])
    order_id = response_body['id']

    order_pk = keys_structure.orders_pk.format(restaurant_id=restaurant_id)
    order_sk = keys_structure.orders_sk.format(user_id=id_user, order_id=order_id)

    def resource_teardown():
        db.get_gen_table().delete_item(Key={'partkey': order_pk, 'sortkey': order_sk})
    request.addfinalizer(resource_teardown)

    assert response_body['id'] == pre_order_id
    assert response_body['user_id'] == id_user
    assert response_body['user_phone_number'] == '+79216146600'
    assert response_body['user_email'] == 'rachko.a@gmail.com'
    assert response_body['restaurant_id'] == restaurant_id
    assert response_body['delivery_address'] == 'Mayskiy lane, 2, flat 119'
    assert len(response_body['item_ids']) == 2
    assert response_body['amount'] == 28.49
    assert response_body['paid'] is False
    assert response_body['history'] == ['created']
    assert response_body['archived'] is False
    assert response_body['comment'] == 'Please deliver my order ASAP'
    assert response_body['feedback'] is None


@pytest.mark.local_db_test
def test_get_order_by_id_authorized_user(chalice_gateway, request):
    restaurant_id = create_test_restaurant(chalice_gateway, request)
    menu_item_id, menu_item_id_2 = create_test_menu_items(chalice_gateway, restaurant_id, request)
    add_test_items_to_cart(chalice_gateway, restaurant_id, [menu_item_id, menu_item_id_2], request)
    pre_order_id = create_test_pre_order_authorized_user(chalice_gateway, request)
    order_id = create_test_order_authorized_user(chalice_gateway, pre_order_id, restaurant_id, request)

    response = make_request(chalice_gateway, endpoint=f"/orders/id/{restaurant_id}/{order_id}",
                            token=id_user, method="GET")

    response_body = json.loads(response["body"])

    assert response['statusCode'] == http200, f"status code not as expected"

    assert response_body['id'] == order_id
    assert response_body['user_id'] == id_user
    assert response_body['user_phone_number'] == '+79216146600'
    assert response_body['user_email'] == 'rachko.a@gmail.com'
    assert response_body['restaurant_id'] == restaurant_id
    assert response_body['delivery_address'] == 'Mayskiy lane, 2, flat 119'
    assert len(response_body['item_ids']) == 2
    assert response_body['amount'] == 28.49
    assert response_body['paid'] is False
    assert response_body['history'] == ['created']
    assert response_body['archived'] is False
    assert response_body['comment'] == 'Please deliver my order ASAP'
    assert response_body['feedback'] is None


def get_orders_base(chalice_gateway, request, url, token, restaurant_id=None):
    if not restaurant_id:
        restaurant_id = create_test_restaurant(chalice_gateway, request)
    menu_item_id, menu_item_id_2 = create_test_menu_items(chalice_gateway, restaurant_id, request)
    add_test_items_to_cart(chalice_gateway, restaurant_id, [menu_item_id], request)
    pre_order_id = create_test_pre_order_authorized_user(chalice_gateway, request)
    order_id = create_test_order_authorized_user(chalice_gateway, pre_order_id, restaurant_id, request)
    add_test_items_to_cart(chalice_gateway, restaurant_id, [menu_item_id_2], request)
    pre_order_id_2 = create_test_pre_order_authorized_user(chalice_gateway, request)
    order_id_2 = create_test_order_authorized_user(chalice_gateway, pre_order_id_2, restaurant_id, request)

    response = make_request(chalice_gateway, endpoint=url, token=token, method="GET")

    response_body = json.loads(response["body"])
    assert response['statusCode'] == http200, f"status code not as expected"
    assert len(response_body) == 2
    assert response_body[0]['id'] != response_body[1]['id']
    for id_ in [order_id, order_id_2]:
        assert id_ in [response_body[0]['id'], response_body[1]['id']]
    for amount in [9.99, 18.50]:
        assert amount in [response_body[0]['amount'], response_body[1]['amount']]


@pytest.mark.local_db_test
def test_get_orders(chalice_gateway, request):
    get_orders_base(chalice_gateway, request, f"/orders", id_user)


@pytest.mark.local_db_test
def test_admin_get_user_orders(chalice_gateway, request):
    get_orders_base(chalice_gateway, request, f"/orders/user/{id_user}", id_admin)


@pytest.mark.local_db_test
def test_rest_manager_get_restaurant_orders(chalice_gateway, request):
    restaurant_id = create_test_restaurant(chalice_gateway, request)
    get_orders_base(chalice_gateway, request, f"/orders/restaurant/{restaurant_id}",
                    id_restaurant_manager, restaurant_id=restaurant_id)
