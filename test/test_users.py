import json

from chalicelib.constants import keys_structure
from test.utils.request_utils import make_request
from chalicelib.utils import db

from test.utils.fixtures import chalice_gateway


def create_test_user(request):
    id_ = "eaa45e81-c17a-4da3-bdee-149919ca531b"
    user_db_record = {
        "partkey": "users_",
        "sortkey": "eaa45e81-c17a-4da3-bdee-149919ca531b",
        "id_": id_,
        "login": "+79061234567",
        "role": "user",
        "phone": "+79061234567",
        "email": "user@test.ru",
        "first_name": "test",
        "last_name": "user",
        "addresses": ['Kaliningrad', 'Vilnius'],
        "date_updated": "2022-12-03T00:26:30",
        "date_created": "2022-12-03T00:26:30",
        "additional_phone_numbers": ['+37066042239'],
    }

    db.put_db_record(user_db_record)

    def resource_teardown_rest():
        db.get_gen_table().delete_item(Key={
            'partkey': keys_structure.users_pk,
            'sortkey': keys_structure.users_sk.format(user_id=id_)
        })
    request.addfinalizer(resource_teardown_rest)
    return id_


def test_user_get(chalice_gateway, request):
    user_id = create_test_user(request)
    response = make_request(chalice_gateway, endpoint="/users", method="GET", token=user_id)

    response_body = json.loads(response["body"])
    assert response_body['id'] == user_id
    assert response_body['login'] == "+79061234567"
    assert response_body['role'] == "user"
    assert response_body['phone'] == "+79061234567"
    assert response_body['email'] == "user@test.ru"
    assert response_body['first_name'] == "test"
    assert response_body['last_name'] == "user"
    assert response_body['addresses'] == ['Kaliningrad', 'Vilnius']
    assert response_body['additional_phone_numbers'] == ['+37066042239']


def test_user_update(chalice_gateway, request):
    user_id = create_test_user(request)

    update_body = {
        'role': 'admin',
        'first_name': 'updated_test',
        'addresses': ['Kaliningrad'],
        'additional_phone_numbers': ['+37066042239', '+79216146600'],
        'unexpected_field': 'unexpected_value'
    }
    response_put = make_request(chalice_gateway, endpoint="/users", method="PUT", json_body=update_body, token=user_id)
    assert response_put['statusCode'] == 200

    response_get = make_request(chalice_gateway, endpoint="/users", method="GET", token=user_id)

    response_body = json.loads(response_get["body"])
    assert response_body['id'] == user_id
    assert response_body['login'] == "+79061234567"
    assert response_body['role'] == "user"
    assert response_body['phone'] == "+79061234567"
    assert response_body['email'] == "user@test.ru"
    assert response_body['first_name'] == "updated_test"
    assert response_body['last_name'] == "user"
    assert response_body['addresses'] == ['Kaliningrad']
    assert response_body['additional_phone_numbers'] == ['+37066042239', '+79216146600']
    assert 'unexpected_field' not in response_body
