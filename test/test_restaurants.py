import json

import pytest as pytest

from chalicelib.constants import keys_structure
from chalicelib.constants.status_codes import http200
from chalicelib.utils import db
from test.utils.request_utils import make_request

from test.utils.fixtures import chalice_gateway

token_admin = 'admin'
token_user = 'user'
token_restaurant_manager = 'restaurant_manager'

id_admin = '13303309-d941-486f-b600-3e90929ac50f'
id_restaurant_manager = '8178f948-cdc2-4e8c-b013-07a956e7e72a'
id_user = 'e5b01491-e538-4be3-8d3c-a57db7fc43c1'


@pytest.mark.local_db_test
def test_create_restaurant(chalice_gateway, request):
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

    response_body = json.loads(response["body"])

    pk = keys_structure.restaurants_pk
    sk = keys_structure.restaurants_sk.format(restaurant_id=response_body["id"])

    def resource_teardown():
        db.get_gen_table().delete_item(Key={'partkey': pk, 'sortkey': sk})
    request.addfinalizer(resource_teardown)

    assert response['statusCode'] == http200, f"status code not as expected"
    assert 'id' in response_body
    db_record = db.get_gen_table().get_item(Key={'partkey': pk, 'sortkey': sk})['Item']
    for key in restaurant_to_create:
        assert restaurant_to_create[key] == db_record[key]
    assert db_record['archived'] is False


@pytest.mark.local_db_test
def test_get_restaurants(chalice_gateway, request):
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

    response_body = json.loads(response["body"])
    restaurant_id = response_body["id"]
    pk = keys_structure.restaurants_pk
    sk = keys_structure.restaurants_sk.format(restaurant_id=restaurant_id)

    def resource_teardown():
        db.get_gen_table().delete_item(Key={'partkey': pk, 'sortkey': sk})
    request.addfinalizer(resource_teardown)

    response_get = make_request(chalice_gateway, endpoint="/restaurants", method="GET", token=id_user)

    response_body_get = json.loads(response_get["body"])

    assert response_get['statusCode'] == http200, f"status code not as expected"
    assert isinstance(response_body_get, list)
    assert len([restaurant for restaurant in response_body_get if restaurant['id'] == restaurant_id]) == 1


@pytest.mark.local_db_test
def test_get_restaurant_by_id(chalice_gateway, request):
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

    response_body = json.loads(response["body"])

    pk = keys_structure.restaurants_pk
    sk = keys_structure.restaurants_sk.format(restaurant_id=response_body["id"])

    def resource_teardown():
        db.get_gen_table().delete_item(Key={'partkey': pk, 'sortkey': sk})
    request.addfinalizer(resource_teardown)

    response_get = make_request(chalice_gateway, endpoint=f"/restaurants/{response_body['id']}",
                                method="GET", token=id_admin)

    response_body_get = json.loads(response_get["body"])
    assert response_get['statusCode'] == http200, f"status code not as expected"
    assert isinstance(response_body_get, dict)
    assert response_body['id'] == response_body_get['id']


@pytest.mark.local_db_test
def test_update_restaurant(chalice_gateway, request):
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

    response_body = json.loads(response["body"])

    pk = keys_structure.restaurants_pk
    sk = keys_structure.restaurants_sk.format(restaurant_id=response_body["id"])

    def resource_teardown():
        db.get_gen_table().delete_item(Key={'partkey': pk, 'sortkey': sk})
    request.addfinalizer(resource_teardown)

    fields_to_update = {
        'title': 'updated restaurant title',
        'address': 'Time Square, New York, USA',
        'description': "This is my test restaurant",
        'cuisine': ['Chinese', 'Japanese']
    }
    wrong_fields_to_update = {
        'created_by': 'wrong_string',
        'closing_time': 'asd',
        'new_field': 'new_value'
    }
    response = make_request(chalice_gateway, endpoint=f"/restaurants/{response_body['id']}", method="PUT",
                            json_body={**fields_to_update, **wrong_fields_to_update}, token=id_admin)

    assert response['statusCode'] == http200, f"status code not as expected"

    db_record = db.get_gen_table().get_item(Key={'partkey': pk, 'sortkey': sk})['Item']
    for key in fields_to_update:
        assert fields_to_update[key] == db_record[key]
    for key in wrong_fields_to_update:
        assert wrong_fields_to_update[key] != db_record.get(key)
    assert db_record['archived'] is False


@pytest.mark.local_db_test
def test_archive_restaurant(chalice_gateway, request):
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

    response_body = json.loads(response["body"])

    pk = keys_structure.restaurants_pk
    sk = keys_structure.restaurants_sk.format(restaurant_id=response_body["id"])

    def resource_teardown():
        db.get_gen_table().delete_item(Key={'partkey': pk, 'sortkey': sk})
    request.addfinalizer(resource_teardown)

    response = make_request(chalice_gateway, endpoint=f"/restaurants/{response_body['id']}",
                            method="DELETE", json_body={}, token=id_admin)

    assert response['statusCode'] == http200, f"status code not as expected"

    db_record = db.get_gen_table().get_item(Key={'partkey': pk, 'sortkey': sk})['Item']
    assert db_record['archived'] is True
