from chalice.test import Client
from app import app


def test_index():
    with Client(app) as client:
        response = client.http.get('/health-check', headers={'Authorization': 'health-check'})
        assert response.json_body == {'health': 'check'}
