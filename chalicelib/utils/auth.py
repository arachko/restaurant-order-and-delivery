import os
import uuid
import jwt
import json

from chalice import Response

# from chalicelib.constants.auth import COGNITO_JWK_URL, COGNITO_IDP_URL
from chalicelib.constants import status_codes, keys_structure
from chalicelib.utils import exceptions as utils_exceptions, db as utils_db
from chalicelib.utils.app import error_response
from chalicelib.utils.logger import log_request, logger, log_exception


def get_user_role(user_id):
    return utils_db.get_db_item(
        partkey=keys_structure.users_pk,
        sortkey=keys_structure.users_sk.format(user_id=user_id)
    ).get('role')


def authenticate(func):
    """
    Wrapper for functions which require user's authentication
    """

    def result_auth(*args, **kwargs):
        try:
            request = args[0]
            log_request(request)
            # body, username, groups, user_id, user_email = auth_result_cognito_v1(request)  # Todo: test auth added
            user_id = request.headers['authorization']
            user_role = get_user_role(user_id)
            company_id = 'aee9d9e6-eb8d-4105-b805-6937d6d6700f'
            if user_id:
                setattr(request, 'auth_result', {'user_id': user_id, 'role': user_role, 'company_id': company_id})
                result = func(*args, **kwargs)
                logger.info(f'authenticate ::: SUCCESS, func.__name__ {func.__name__}')
                return result
            else:
                raise utils_exceptions.NotAuthorizedException('Error occurred in authorization process')
        except Exception as err:
            logger.error(f"authenticate ::: {str(err)}")
            return error_response(err, msg=f'{func.__name__}')

    return result_auth


def authenticate_class(func):
    """
    Wrapper for class methods which require user's authentication
    """

    def result_auth(*args, **kwargs):
        try:
            instance = args[0]
            request = args[1]
            log_request(request)
            # body, username, groups, user_id, user_email = auth_result_cognito_v1(request)  # Todo: test auth added
            user_id = request.headers['authorization']
            user_role = get_user_role(user_id)
            company_id = 'aee9d9e6-eb8d-4105-b805-6937d6d6700f'
            if user_id:
                setattr(request, 'auth_result', {'user_id': user_id, 'role': user_role, 'company_id': company_id})
                setattr(instance, 'user_id', user_id)
                setattr(instance, 'role', user_role)
                setattr(instance, 'company_id', company_id)
                return func(*args, **kwargs)
            else:
                raise utils_exceptions.NotAuthorizedException('Error occurred in authorization process')
        except Exception as err:
            logger.error(f"authenticate_class ::: {str(err)}")
            return error_response(err, msg=f'{func.__name__}')

    return result_auth


# def auth_result_cognito_v1(current_request):
#     """ This function shall replace the above function soon """
#     try:
#         current_request_id = str(uuid.uuid4()).split('-')[4]
#         logger.current_request_id = current_request_id
#         setattr(current_request, 'short_request_id', current_request_id)
#         logger.debug(f'auth_result_cognito: current_request={current_request.to_dict()}')
#         token = current_request.headers['authorization']
#         print(f'auth_result_cognito: current_request={current_request.to_dict()}')
#         jwks_client = jwt.PyJWKClient(COGNITO_JWK_URL)
#         signing_key = jwks_client.get_signing_key_from_jwt(token)
#         decoded_jwt_token = jwt.decode(
#             token,
#             signing_key.key,
#             algorithms=['RS256'],
#             audience=os.environ['COGNITO_CLIENT_ID_WEB'],
#             issuer=COGNITO_IDP_URL)
#         logger.debug(f'auth_result_cognito: token decoded={decoded_jwt_token}')
#
#         username = decoded_jwt_token['cognito:username']
#         groups = decoded_jwt_token.get('cognito:groups', [])
#         user_id = decoded_jwt_token['sub']
#         user_email = decoded_jwt_token['email']
#         logger.debug('username is taken from decoded id_token')
#         body = {'message': 'auth_result_cognito no errors'}
#         log_message = {
#             'auth_result_cognito': {
#                 'username': username,
#                 'groups': groups,
#                 'user_id': user_id,
#                 'user_email': user_email
#             }
#         }
#         logger.info(json.dumps(log_message))
#
#     except Exception as error:
#         setattr(error, 'LEVEL', 'error')
#         log_exception(error, 401, f"auth_result_cognito_v1 ::: {error}")
#         raise utils_exceptions.AuthorizationException(error)
#     else:
#         return body, username, groups, user_id, user_email
