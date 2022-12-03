import json
from decimal import Decimal

import pytest as pytest

from chalicelib.constants import keys_structure
from chalicelib.constants.status_codes import http200
from chalicelib.utils import db
from test.utils.request_utils import make_request

from test.utils.fixtures import chalice_gateway

token_admin = 'admin'
token_restaurant_manager = 'restaurant_manager'
token_user = 'user'

test_user_id = '13303309-d941-486f-b600-3e90929ac50f'


def create_test_restaurant(chalice_gateway):
    restaurant_to_create = {
        'title': 'test restaurant title',
        'address': 'Time Square, New York',
        'description': "This is my test restaurant",
        'cuisine': ['Chinese'],
        'opening_time': 10,
        'closing_time': 23
    }
    response = make_request(chalice_gateway, endpoint="/restaurants", method="POST",
                            json_body=restaurant_to_create, token=token_admin)
    id_ = json.loads(response["body"])["id"]
    pk = keys_structure.restaurants_pk
    sk = keys_structure.restaurants_sk.format(restaurant_id=id_)
    return id_, pk, sk


def create_test_menu_item(chalice_gateway, restaurant_id):
    menu_item_to_create = {
        'title': 'test title',
        'category': 'breakfast',
        'description': 'some description of menu item',
        'price': 130
    }
    response = make_request(chalice_gateway, endpoint=f"/menu-items/{restaurant_id}", method="POST",
                            json_body=menu_item_to_create, token=token_restaurant_manager)

    id_ = json.loads(response["body"])["id"]
    pk = keys_structure.menu_items_pk.format(restaurant_id=restaurant_id)
    sk = keys_structure.menu_items_sk.format(menu_item_id=id_)
    return id_, pk, sk


@pytest.mark.local_db_test
def test_get_cart(chalice_gateway, request):
    response = make_request(chalice_gateway, endpoint=f"/carts", method="GET")

    response_body = json.loads(response["body"]).get('cart')

    assert response['statusCode'] == http200, f"status code not as expected"
    assert response_body['user_id'] == test_user_id
    assert response_body['restaurant_id'] is None
    assert response_body['delivery_address'] is None
    assert response_body['delivery_price'] is None
    assert response_body['items'] == []


@pytest.mark.local_db_test
def test_add_item_to_cart(chalice_gateway, request):
    restaurant_id, restaurant_pk, restaurant_sk = create_test_restaurant(chalice_gateway)
    menu_item_id, menu_item_pk, menu_item_sk = create_test_menu_item(chalice_gateway, restaurant_id)

    carts_pk, carts_sk = keys_structure.carts_pk, keys_structure.carts_sk.format(user_id=test_user_id)

    response = make_request(chalice_gateway, endpoint=f"/carts/{restaurant_id}/{menu_item_id}", method="POST",
                            json_body={'address': 'test_address'}, token=token_user)

    assert response['statusCode'] == http200, f"status code not as expected"

    def resource_teardown():
        db.get_gen_table().delete_item(Key={'partkey': restaurant_pk, 'sortkey': restaurant_sk})
        db.get_gen_table().delete_item(Key={'partkey': menu_item_pk, 'sortkey': menu_item_sk})
        db.get_gen_table().delete_item(Key={'partkey': carts_pk, 'sortkey': carts_sk})
    request.addfinalizer(resource_teardown)

    def assert_cart_details(assert_dict, from_db=False):
        assert assert_dict['user_id'] == test_user_id
        assert assert_dict['restaurant_id'] == restaurant_id
        assert assert_dict['delivery_address'] == 'test_address'
        assert assert_dict['delivery_price'] == 0.0
        assert assert_dict['items' if from_db is False else 'items_'] == [menu_item_id]
        if from_db is False:
            assert 'partkey' not in assert_dict
            assert 'sortkey' not in assert_dict

    cart = json.loads(response["body"]).get('cart')
    assert_cart_details(cart)

    db_record = db.get_gen_table().get_item(Key={'partkey': carts_pk, 'sortkey': carts_sk})['Item']
    assert_cart_details(db_record, from_db=True)

    response_get = make_request(chalice_gateway, endpoint=f"/carts", method="GET")
    cart = json.loads(response_get["body"]).get('cart')
    assert_cart_details(cart)


@pytest.mark.local_db_test
def test_remove_item_from_cart(chalice_gateway, request):
    restaurant_id, restaurant_pk, restaurant_sk = create_test_restaurant(chalice_gateway)
    menu_item_id, menu_item_pk, menu_item_sk = create_test_menu_item(chalice_gateway, restaurant_id)

    carts_pk, carts_sk = keys_structure.carts_pk, keys_structure.carts_sk.format(user_id=test_user_id)

    response = make_request(chalice_gateway, endpoint=f"/carts/{restaurant_id}/{menu_item_id}", method="POST",
                            json_body={'address': 'test_address'}, token=token_user)

    assert response['statusCode'] == http200, f"status code not as expected"

    def resource_teardown():
        db.get_gen_table().delete_item(Key={'partkey': restaurant_pk, 'sortkey': restaurant_sk})
        db.get_gen_table().delete_item(Key={'partkey': menu_item_pk, 'sortkey': menu_item_sk})
        db.get_gen_table().delete_item(Key={'partkey': carts_pk, 'sortkey': carts_sk})
    request.addfinalizer(resource_teardown)

    def assert_cart_details(assert_dict, from_db=False, items=None):
        if items is None:
            items = [menu_item_id]
        assert assert_dict['user_id'] == test_user_id
        assert assert_dict['restaurant_id'] == restaurant_id
        assert assert_dict['delivery_address'] == 'test_address'
        assert assert_dict['delivery_price'] == 0.0
        assert assert_dict['items' if from_db is False else 'items_'] == items
        if from_db is False:
            assert 'partkey' not in assert_dict
            assert 'sortkey' not in assert_dict

    db_record = db.get_gen_table().get_item(Key={'partkey': carts_pk, 'sortkey': carts_sk})['Item']
    assert_cart_details(db_record, from_db=True)

    response_get = make_request(chalice_gateway, endpoint=f"/carts/{menu_item_id}", method="DELETE")
    cart = json.loads(response_get["body"]).get('cart')
    assert_cart_details(cart, items=[])

    db_record = db.get_gen_table().get_item(Key={'partkey': carts_pk, 'sortkey': carts_sk})['Item']
    assert_cart_details(db_record, from_db=True, items=[])


@pytest.mark.local_db_test
def test_clear_cart(chalice_gateway, request):
    restaurant_id, restaurant_pk, restaurant_sk = create_test_restaurant(chalice_gateway)
    menu_item_id, menu_item_pk, menu_item_sk = create_test_menu_item(chalice_gateway, restaurant_id)

    carts_pk, carts_sk = keys_structure.carts_pk, keys_structure.carts_sk.format(user_id=test_user_id)

    response = make_request(chalice_gateway, endpoint=f"/carts/{restaurant_id}/{menu_item_id}", method="POST",
                            json_body={'address': 'test_address'}, token=token_user)

    assert response['statusCode'] == http200, f"status code not as expected"

    def resource_teardown():
        db.get_gen_table().delete_item(Key={'partkey': restaurant_pk, 'sortkey': restaurant_sk})
        db.get_gen_table().delete_item(Key={'partkey': menu_item_pk, 'sortkey': menu_item_sk})
        db.get_gen_table().delete_item(Key={'partkey': carts_pk, 'sortkey': carts_sk})
    request.addfinalizer(resource_teardown)

    def assert_cart_details(assert_dict):
        assert assert_dict['user_id'] == test_user_id
        assert assert_dict['restaurant_id'] == restaurant_id
        assert assert_dict['delivery_address'] == 'test_address'
        assert assert_dict['delivery_price'] == 0.0
        assert assert_dict['items_'] == [menu_item_id]

    db_record = db.get_gen_table().get_item(Key={'partkey': carts_pk, 'sortkey': carts_sk})['Item']
    assert_cart_details(db_record)

    response_get = make_request(chalice_gateway, endpoint=f"/carts", method="DELETE")
    assert json.loads(response_get["body"]).get('message') == 'Cart was successfully cleared'

    get_db_record_response = db.get_gen_table().get_item(Key={'partkey': carts_pk, 'sortkey': carts_sk})
    assert 'Item' not in get_db_record_response
