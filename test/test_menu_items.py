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

    def resource_teardown_restaurant():
        db.get_customers_table().delete_item(Key={
            'partkey': keys_structure.restaurants_pk.format(company_id=test_company_id),
            'sortkey': keys_structure.restaurants_sk.format(restaurant_id=id_)
        })
    request.addfinalizer(resource_teardown_restaurant)

    return id_


def create_test_menu_item(chalice_gateway, restaurant_id, request):
    menu_item_to_create = {
        'title': 'test title',
        'category': 'breakfast',
        'description': 'some description of menu item',
        'price': 130.99
    }
    response = make_request(chalice_gateway, endpoint=f"/menu-items/{restaurant_id}", method="POST",
                            json_body=menu_item_to_create, token=id_restaurant_manager)

    id_ = json.loads(response["body"])["id"]

    def resource_teardown_menu_item():
        db.get_customers_table().delete_item(Key={
            'partkey': keys_structure.menu_items_pk.format(company_id=test_company_id, restaurant_id=restaurant_id),
            'sortkey': keys_structure.menu_items_sk.format(menu_item_id=id_)
        })
    request.addfinalizer(resource_teardown_menu_item)

    return id_


@pytest.mark.local_db_test
def test_create_menu_item(chalice_gateway, request):
    restaurant_id = create_test_restaurant(chalice_gateway, request)

    menu_item_to_create = {
        'title': 'test title',
        'category': 'breakfast',
        'description': 'some description of menu item',
        'price': 130
    }

    response = make_request(chalice_gateway, endpoint=f"/menu-items/{restaurant_id}", method="POST",
                            json_body=menu_item_to_create, token=id_restaurant_manager)

    response_body = json.loads(response["body"])

    assert response['statusCode'] == http200, f"status code not as expected"
    assert 'id' in response_body

    def resource_teardown_menu_item():
        db.get_customers_table().delete_item(Key={
            'partkey': keys_structure.menu_items_pk.format(company_id=test_company_id, restaurant_id=restaurant_id),
            'sortkey': keys_structure.menu_items_sk.format(menu_item_id=response_body['id'])
        })
    request.addfinalizer(resource_teardown_menu_item)

    db_record = db.get_customers_table().get_item(Key={
        'partkey': keys_structure.menu_items_pk.format(company_id=test_company_id, restaurant_id=restaurant_id),
        'sortkey': keys_structure.menu_items_sk.format(menu_item_id=response_body['id'])
    })['Item']

    for key in menu_item_to_create:
        assert menu_item_to_create[key] == db_record[key]
    assert db_record['archived'] is False


@pytest.mark.local_db_test
def test_get_menu_items(chalice_gateway, request):
    restaurant_id = create_test_restaurant(chalice_gateway, request)
    menu_item_id = create_test_menu_item(chalice_gateway, restaurant_id, request)

    response_get = make_request(chalice_gateway, endpoint=f"/menu-items/{restaurant_id}", method="GET")

    response_body_get = json.loads(response_get["body"])
    assert response_get['statusCode'] == http200, f"status code not as expected"
    assert response_body_get[0]['price'] == 130.99
    assert isinstance(response_body_get, list)
    assert len([menu_item for menu_item in response_body_get if menu_item['id'] == menu_item_id]) == 1


@pytest.mark.local_db_test
def test_update_menu_item(chalice_gateway, request):
    restaurant_id = create_test_restaurant(chalice_gateway, request)
    menu_item_id = create_test_menu_item(chalice_gateway, restaurant_id, request)

    fields_to_update = {
        'title': 'updated menu item title',
        'price': 180.55,
        'description': "This is my updated menu item description",
        'opening_time': 12,
        'is_available': False
    }
    wrong_fields_to_update = {
        'created_by': 'wrong_string',
        'closing_time': 'asd',
        'new_field': 'new_value'
    }
    response = make_request(chalice_gateway, endpoint=f"/menu-items/{restaurant_id}/{menu_item_id}", method="PUT",
                            json_body={**fields_to_update, **wrong_fields_to_update}, token=id_restaurant_manager)

    assert response['statusCode'] == http200, f"status code not as expected"

    db_record = db.get_customers_table().get_item(Key={
        'partkey': keys_structure.menu_items_pk.format(company_id=test_company_id, restaurant_id=restaurant_id),
        'sortkey': keys_structure.menu_items_sk.format(menu_item_id=menu_item_id)
    })['Item']

    for key in fields_to_update:
        if type(db_record[key]) == Decimal:
            db_record[key] = float(db_record[key])
        assert fields_to_update[key] == db_record[key]
    for key in wrong_fields_to_update:
        assert wrong_fields_to_update[key] != db_record.get(key)
    assert db_record['archived'] is False


@pytest.mark.local_db_test
def test_archive_menu_item(chalice_gateway, request):
    restaurant_id = create_test_restaurant(chalice_gateway, request)
    menu_item_id = create_test_menu_item(chalice_gateway, restaurant_id, request)

    response = make_request(chalice_gateway, endpoint=f"/menu-items/{restaurant_id}/{menu_item_id}",
                            method="DELETE", token=id_restaurant_manager)

    assert response['statusCode'] == http200, f"status code not as expected"

    db_record = db.get_customers_table().get_item(Key={
        'partkey': keys_structure.menu_items_pk.format(company_id=test_company_id, restaurant_id=restaurant_id),
        'sortkey': keys_structure.menu_items_sk.format(menu_item_id=menu_item_id)
    })['Item']
    assert db_record['archived'] is True
