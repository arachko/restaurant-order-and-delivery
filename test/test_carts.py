import json
from decimal import Decimal

import pytest as pytest

from chalicelib.constants import keys_structure
from chalicelib.constants.status_codes import http200
from chalicelib.utils import db
from chalicelib.utils.auth import host_company_id_map
from test.utils.request_utils import make_request

from test.utils.fixtures import chalice_gateway

token_admin = 'admin'
token_restaurant_manager = 'restaurant_manager'
token_user = 'user'

id_admin = '13303309-d941-486f-b600-3e90929ac50f'
id_restaurant_manager = '8178f948-cdc2-4e8c-b013-07a956e7e72a'
id_user = 'e5b01491-e538-4be3-8d3c-a57db7fc43c1'

test_company_id = host_company_id_map['test-domain.com']


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

    def resource_teardown():
        db.get_gen_table().delete_item(Key={
            'partkey': keys_structure.restaurants_pk.format(company_id=test_company_id),
            'sortkey': keys_structure.restaurants_sk.format(restaurant_id=id_)
        })
    request.addfinalizer(resource_teardown)

    return id_


def create_test_menu_item(chalice_gateway, restaurant_id, request):
    menu_item_to_create = {
        'title': 'test title',
        'category': 'breakfast',
        'description': 'some description of menu item',
        'price': 130
    }
    response = make_request(chalice_gateway, endpoint=f"/menu-items/{restaurant_id}", method="POST",
                            json_body=menu_item_to_create, token=id_restaurant_manager)

    id_ = json.loads(response["body"])["id"]

    def resource_teardown():
        db.get_gen_table().delete_item(Key={
            'partkey': keys_structure.menu_items_pk.format(company_id=test_company_id, restaurant_id=restaurant_id),
            'sortkey': keys_structure.menu_items_sk.format(menu_item_id=id_)
        })
    request.addfinalizer(resource_teardown)

    return id_


def add_test_item_to_cart(chalice_gateway, restaurant_id, menu_item_id, request):
    req_body = {
        'restaurant_id': restaurant_id,
        'menu_item_id': menu_item_id,
        'qty': 3
    }

    response = make_request(chalice_gateway, endpoint=f"/carts", json_body=req_body, method="POST", token=id_user)

    assert response['statusCode'] == http200, f"status code not as expected"

    carts_pk, carts_sk = keys_structure.carts_pk.format(company_id=test_company_id), \
        keys_structure.carts_sk.format(user_id=id_user)

    def resource_teardown():
        db.get_gen_table().delete_item(Key={'partkey': carts_pk, 'sortkey': carts_sk})
    request.addfinalizer(resource_teardown)


@pytest.mark.local_db_test
def test_get_cart(chalice_gateway, request):
    response = make_request(chalice_gateway, endpoint=f"/carts", method="GET", token=id_user)

    response_body = json.loads(response["body"]).get('cart')

    assert response['statusCode'] == http200, f"status code not as expected"
    assert response_body['id'] == id_user
    assert response_body['restaurant_id'] is None
    assert response_body['delivery_address'] is None
    assert response_body['menu_items'] == {}


@pytest.mark.local_db_test
def test_add_item_to_cart(chalice_gateway, request):
    restaurant_id = create_test_restaurant(chalice_gateway, request)
    menu_item_id = create_test_menu_item(chalice_gateway, restaurant_id, request)

    carts_pk, carts_sk = keys_structure.carts_pk.format(company_id=test_company_id), \
        keys_structure.carts_sk.format(user_id=id_user)

    req_body = {
        'restaurant_id': restaurant_id,
        'menu_item_id': menu_item_id,
        'qty': 2
    }

    response = make_request(chalice_gateway, endpoint=f"/carts", json_body=req_body, method="POST", token=id_user)

    assert response['statusCode'] == http200, f"status code not as expected"

    def resource_teardown():
        db.get_gen_table().delete_item(Key={'partkey': carts_pk, 'sortkey': carts_sk})
    request.addfinalizer(resource_teardown)

    def assert_cart_details(assert_dict, from_db=False):
        assert id_user in [assert_dict.get('id_'), assert_dict.get('id')]
        assert assert_dict['restaurant_id'] == restaurant_id
        assert assert_dict['menu_items'] == {menu_item_id: {'id': menu_item_id, 'qty': 2}}
        if from_db is False:
            assert 'partkey' not in assert_dict
            assert 'sortkey' not in assert_dict

    cart = json.loads(response["body"]).get('cart')
    assert_cart_details(cart)

    db_record = db.get_gen_table().get_item(Key={'partkey': carts_pk, 'sortkey': carts_sk})['Item']
    assert_cart_details(db_record, from_db=True)

    response_get = make_request(chalice_gateway, endpoint=f"/carts", method="GET", token=id_user)
    cart = json.loads(response_get["body"]).get('cart')
    assert_cart_details(cart)


@pytest.mark.local_db_test
def test_remove_item_from_cart(chalice_gateway, request):
    restaurant_id = create_test_restaurant(chalice_gateway, request)
    menu_item_id = create_test_menu_item(chalice_gateway, restaurant_id, request)
    add_test_item_to_cart(chalice_gateway, restaurant_id, menu_item_id, request)

    carts_pk, carts_sk = keys_structure.carts_pk.format(company_id=test_company_id), \
        keys_structure.carts_sk.format(user_id=id_user)

    def assert_cart_details(assert_dict, from_db=False, menu_items=None):
        if menu_items is None:
            menu_items = {menu_item_id: {'id': menu_item_id, 'qty': Decimal('3')}}
        assert id_user in [assert_dict.get('id_'), assert_dict.get('id')]
        assert assert_dict['restaurant_id'] == restaurant_id
        assert assert_dict['menu_items'] == menu_items
        if from_db is False:
            assert 'partkey' not in assert_dict
            assert 'sortkey' not in assert_dict

    db_record = db.get_gen_table().get_item(Key={'partkey': carts_pk, 'sortkey': carts_sk})['Item']
    assert_cart_details(db_record, from_db=True)

    response_get = make_request(chalice_gateway, endpoint=f"/carts/{menu_item_id}", method="DELETE", token=id_user)
    cart = json.loads(response_get["body"]).get('cart')
    assert_cart_details(cart, menu_items={})

    db_record = db.get_gen_table().get_item(Key={'partkey': carts_pk, 'sortkey': carts_sk})['Item']
    assert_cart_details(db_record, from_db=True, menu_items={})


@pytest.mark.local_db_test
def test_clear_cart(chalice_gateway, request):
    restaurant_id = create_test_restaurant(chalice_gateway, request)
    menu_item_id = create_test_menu_item(chalice_gateway, restaurant_id, request)
    add_test_item_to_cart(chalice_gateway, restaurant_id, menu_item_id, request)

    carts_pk, carts_sk = keys_structure.carts_pk.format(company_id=test_company_id), \
        keys_structure.carts_sk.format(user_id=id_user)

    def assert_cart_details(assert_dict):
        assert assert_dict['id_'] == id_user
        assert assert_dict['restaurant_id'] == restaurant_id
        assert assert_dict['menu_items'] == {menu_item_id: {'id': menu_item_id, 'qty': Decimal('3')}}

    db_record = db.get_gen_table().get_item(Key={'partkey': carts_pk, 'sortkey': carts_sk})['Item']
    assert_cart_details(db_record)

    response_get = make_request(chalice_gateway, endpoint=f"/carts", method="DELETE", token=id_user)
    assert json.loads(response_get["body"]).get('message') == 'Cart was successfully cleared'

    get_db_record_response = db.get_gen_table().get_item(Key={'partkey': carts_pk, 'sortkey': carts_sk})
    assert 'Item' not in get_db_record_response
