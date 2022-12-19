import json

import pytest
from requests_toolbelt.multipart.encoder import MultipartEncoder
from chalicelib.constants import keys_structure
from chalicelib.constants.constants import MAIN_IMAGE_NAME, THUMB_IMAGE_NAME
from chalicelib.constants.status_codes import http200
from chalicelib.utils import db
from chalicelib.utils.auth import host_company_id_map
from test.utils.request_utils import make_request
from chalicelib.utils.boto_clients import s3_client

from test.utils.fixtures import chalice_gateway

id_admin = '13303309-d941-486f-b600-3e90929ac50f'
id_restaurant_manager = '8178f948-cdc2-4e8c-b013-07a956e7e72a'
id_user = 'e5b01491-e538-4be3-8d3c-a57db7fc43c1'

company_id = 'aee9d9e6-eb8d-4105-b805-6937d6d6700f'

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

    def resource_teardown_rest():
        db.get_gen_table().delete_item(Key={
            'partkey': keys_structure.restaurants_pk.format(company_id=test_company_id),
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
    response = make_request(chalice_gateway, endpoint=f"/menu-items/{restaurant_id}", method="POST",
                            json_body=menu_item_to_create, token=id_restaurant_manager)

    id_ = json.loads(response["body"])["id"]

    def resource_teardown_menu_items():
        db.get_gen_table().delete_item(Key={
            'partkey': keys_structure.menu_items_pk.format(company_id=test_company_id, restaurant_id=restaurant_id),
            'sortkey': keys_structure.menu_items_sk.format(menu_item_id=id_)
        })
    request.addfinalizer(resource_teardown_menu_items)

    return id_


@pytest.mark.skip("Don't run the test each time because it put and delete images in s3 each time")
def test_put_restaurant_image(chalice_gateway, request):
    restaurant_id = create_test_restaurant(chalice_gateway, request)
    multipart_data = MultipartEncoder(
        fields={
            'fileContent': ('test_image.jpg', open('food.jpg', 'rb'), 'image/jpg'),
            'entityType': 'restaurant',
            'restaurantId': restaurant_id
        }
    )
    response = chalice_gateway.handle_request(
        method='POST',
        path='/image-upload',
        headers={'Content-Type': multipart_data.content_type,
                 'Host': 'test-domain.com',
                 'Authorization': id_restaurant_manager},
        body=multipart_data.to_string()
    )

    print(response)
    assert response['statusCode'] == http200, f"status code not as expected"

    def resource_teardown_menu_items():
        s3_client.delete_object(Bucket='restmonster-websites-images-dev',
                                Key=f'{company_id}/{restaurant_id}/images/{MAIN_IMAGE_NAME}')
        s3_client.delete_object(Bucket='restmonster-websites-images-dev',
                                Key=f'{company_id}/{restaurant_id}/images/{THUMB_IMAGE_NAME}')
    request.addfinalizer(resource_teardown_menu_items)

    response_body = json.loads(response["body"])
    assert response_body == {'message': 'restaurant image was updated successfully'}


@pytest.mark.skip("Don't run the test each time because it put and delete images in s3 each time")
def test_put_menu_item_image(chalice_gateway, request):
    restaurant_id = create_test_restaurant(chalice_gateway, request)
    menu_item_id = create_test_menu_items(chalice_gateway, restaurant_id, request)
    multipart_data = MultipartEncoder(
        fields={
            'fileContent': ('test_image.jpg', open('food.jpg', 'rb'), 'image/jpg'),
            'entityType': 'menu_item',
            'restaurantId': restaurant_id,
            'menuItemId': menu_item_id
        }
    )
    response = chalice_gateway.handle_request(
        method='POST',
        path='/image-upload',
        headers={'Content-Type': multipart_data.content_type,
                 'Host': 'test-domain.com',
                 'Authorization': id_restaurant_manager},
        body=multipart_data.to_string()
    )

    print(response)
    assert response['statusCode'] == http200, f"status code not as expected"

    def resource_teardown_menu_items():
        s3_client.delete_object(Bucket='restmonster-websites-images-dev',
                                Key=f'{company_id}/{restaurant_id}/{menu_item_id}/images/{MAIN_IMAGE_NAME}')
        s3_client.delete_object(Bucket='restmonster-websites-images-dev',
                                Key=f'{company_id}/{restaurant_id}/{menu_item_id}/images/{THUMB_IMAGE_NAME}')
    request.addfinalizer(resource_teardown_menu_items)

    response_body = json.loads(response["body"])
    assert response_body == {'message': 'menu_item image was updated successfully'}

