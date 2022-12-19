import json
from typing import Optional
import chalice


def make_request(chalice_gateway, endpoint: str = '/', method: str = 'GET',
                 query: Optional[str] = None, json_body=None, token=None) -> chalice.Response:
    """Request for index endpoint """
    return chalice_gateway.handle_request(
        method=method,
        path=f"{endpoint}?{query}" if query else f"{endpoint}",
        headers={'Content-Type': 'application/json', 'Host': 'test-domain.com', 'Authorization': token},
        body=json.dumps(json_body) if json_body else b''
    )
