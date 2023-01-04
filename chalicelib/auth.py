import os
import uuid
from datetime import datetime
from typing import Dict, Any

from chalice import AuthResponse, AuthRoute
from chalice.app import AuthRequest, ChaliceAuthorizer, Response

from chalicelib.constants.keys_structure import users_pk, users_sk
from chalicelib.users import User
from chalicelib.utils import data as utils_data
from chalicelib.utils.auth import get_company_id_by_host
from chalicelib.utils.boto_clients import cognito_client
from chalicelib.utils.db import get_main_table
from chalicelib.utils.exceptions import AuthorizationException, RecordNotFound, ValidationException
from pycognito import Cognito

from chalicelib.utils.logger import logger

UUID_PATTERN = '????????-????-4???-????-????????????'
ORDER_ID_PATTERN = '????????'


# class CustomAuthRequest(AuthRequest):
#     def __init__(self, auth_type: str, token: str, method_arn: str, request_host: str) -> None:
#         AuthRequest.__init__(self, auth_type, token, method_arn)
#         self.request_host: str = request_host
#
#
# class MonsterAuthorizer(ChaliceAuthorizer):
#     def _transform_event(self, event: Dict[str, Any]) -> CustomAuthRequest:
#         return CustomAuthRequest(event['type'], event['authorizationToken'],
#                                  event['methodArn'], event.get('headers').get('host'))


def role_authorizer(auth_request):
    user_id = auth_request.token
    company_id = 'f770d5f7-6dd2-4cdf-842b-5fd0dd84a52a'
    try:
        user: User = User.init_by_id(company_id, user_id)
    except RecordNotFound:
        return AuthResponse(routes=[], principal_id='')
    if user.role == 'user':
        return AuthResponse(
            routes=[
                AuthRoute(path=f'/users', methods=['GET', 'PUT']),
                AuthRoute(path=f'/restaurants', methods=['GET']),
                AuthRoute(path=f'/restaurants/{UUID_PATTERN}', methods=['GET']),
                AuthRoute(path=f'/restaurants/{UUID_PATTERN}/delivery-price', methods=['POST']),
                AuthRoute(path=f'/menu-items/{UUID_PATTERN}', methods=['GET']),
                AuthRoute(path=f'/carts/{UUID_PATTERN}', methods=['GET', 'POST', 'DELETE']),
                AuthRoute(path=f'/carts/{UUID_PATTERN}/{UUID_PATTERN}', methods=['DELETE']),
                AuthRoute(path=f'/orders', methods=['GET', 'POST']),
                AuthRoute(path=f'/orders/id/{UUID_PATTERN}/{ORDER_ID_PATTERN}', methods=['GET', 'DELETE']),
                AuthRoute(path=f'/orders/archived/*', methods=['GET']),
                AuthRoute(path=f'/orders/pre-order/{UUID_PATTERN}', methods=['POST'])
            ],
            principal_id='user'
        )
    elif user.role == 'restaurant_manager':
        return AuthResponse(
            routes=[
                AuthRoute(path=f'/users', methods=['GET']),
                AuthRoute(path=f'/restaurants', methods=['GET']),
                AuthRoute(path=f'/restaurants/{UUID_PATTERN}', methods=['GET']),
                AuthRoute(path=f'/restaurants/{UUID_PATTERN}/delivery-price', methods=['POST']),
                AuthRoute(path=f'/menu-items/{UUID_PATTERN}', methods=['GET', 'POST']),
                AuthRoute(path=f'/menu-items/{UUID_PATTERN}/{UUID_PATTERN}', methods=['PUT', 'DELETE']),
                AuthRoute(path=f'/orders', methods=['GET']),
                AuthRoute(path=f'/orders/restaurant/{UUID_PATTERN}', methods=['GET']),
                AuthRoute(path=f'/orders/archived/{UUID_PATTERN}', methods=['GET']),
                AuthRoute(path=f'/orders/{UUID_PATTERN}/{ORDER_ID_PATTERN}', methods=['PUT', 'DELETE']),
                AuthRoute(path=f'/image-upload', methods=['POST'])
            ],
            principal_id='restaurant_manager'
        )
    elif user.role == 'company_admin':
        return AuthResponse(
            routes=[
                AuthRoute(path=f'/users', methods=['GET', 'PUT']),
                AuthRoute(path=f'/restaurants', methods=['GET', 'POST']),
                AuthRoute(path=f'/restaurants/{UUID_PATTERN}', methods=['GET']),
                AuthRoute(path=f'/restaurants/{UUID_PATTERN}/delivery-price', methods=['POST']),
                AuthRoute(path=f'/menu-items/{UUID_PATTERN}', methods=['GET', 'POST']),
                AuthRoute(path=f'/menu-items/{UUID_PATTERN}/{UUID_PATTERN}', methods=['PUT', 'DELETE']),
                AuthRoute(path=f'/orders', methods=['GET']),
                AuthRoute(path=f'/orders/restaurant/{UUID_PATTERN}', methods=['GET']),
                AuthRoute(path=f'/orders/archived/{UUID_PATTERN}', methods=['GET']),
                AuthRoute(path=f'/orders/{UUID_PATTERN}/{ORDER_ID_PATTERN}', methods=['PUT', 'DELETE']),
                AuthRoute(path=f'/image-upload', methods=['POST']),
                AuthRoute(path=f'/users/managers', methods=['GET', 'POST', 'DELETE']),
            ],
            principal_id='company_admin'
        )
    elif user.role == 'admin':
        return AuthResponse(
            routes=[
                AuthRoute(path=f'/restaurants', methods=['GET', 'POST']),
                AuthRoute(path=f'/restaurants/{UUID_PATTERN}', methods=['GET', 'PUT', 'DELETE']),
                AuthRoute(path=f'/restaurants/{UUID_PATTERN}/delivery-price', methods=['POST']),
                AuthRoute(path=f'/orders/restaurant/{UUID_PATTERN}', methods=['GET']),
                AuthRoute(path=f'/orders/user/{UUID_PATTERN}', methods=['GET']),
                AuthRoute(path=f'/orders/archived/restaurant/{UUID_PATTERN}/{UUID_PATTERN}', methods=['GET']),
                AuthRoute(path=f'/orders/archived/user/{UUID_PATTERN}/{UUID_PATTERN}', methods=['GET']),
                AuthRoute(path=f'/orders/{UUID_PATTERN}/{ORDER_ID_PATTERN}', methods=['DELETE'])
            ],
            principal_id='admin'
        )
    else:
        return AuthResponse(routes=[], principal_id='')


def login_cognito(current_request):
    body = current_request.json_body
    password = body['password']
    username = body['username']
    try:
        u = Cognito(os.environ['COGNITO_ADMIN_POOL_ID'], os.environ['COGNITO_ADMIN_POOL_CLIENT_ID'],
                    username=username, user_pool_region=os.environ['DEFAULT_REGION'])

        u.authenticate(password=password)
        return {
            'token': u.id_token,
            'id_token': u.id_token,
            'access_token': u.access_token,
            'refresh_token': u.refresh_token
        }
    except Exception as e:
        logger.warning(f'login_cognito(): Exception {e}')
        return {
            'token': None,
            'id_token': None,
            'access_token': None,
            'refresh_token': None
        }


def refresh_id_token_cognito(current_request):
    body = current_request.json_body
    id_token = body['id_token']
    refresh_token = body['refresh_token']
    try:
        u = Cognito(os.environ['COGNITO_ADMIN_POOL_ID'], os.environ['COGNITO_ADMIN_POOL_CLIENT_ID'],
                    id_token=id_token, refresh_token=refresh_token)
        logger.debug(f'original id_token={u.id_token}')

        u.renew_access_token()
        logger.debug(f'refreshed id_token={u.id_token}')
        return Response(status_code=200, body={'status': 'success', 'id_token': f'{u.id_token}'})
    except Exception as e:
        logger.debug(f'refresh_token_cognito(): Exception {e}')
        return Response(status_code=400, body={'status': 'error', 'error': str(e)})


def get_all_cognito_users_email():
    users = cognito_client.list_users(
        UserPoolId=os.environ['COGNITO_ADMIN_POOL_ID'],
        AttributesToGet=['email']
    )['Users']
    all_registered_emails = [user['Attributes'][0]['Value'] for user in users]

    logger.info(f'get_all_cognito_users_email ::: get {len(all_registered_emails)} emails')
    return all_registered_emails


def cognito_pre_signup(event, context):
    logger.info(f'cognito_pre_signup ::: triggered: event={event}, context={context}')
    registered_emails = get_all_cognito_users_email()

    new_user_email = event['request']['userAttributes'].get('email')
    if new_user_email in registered_emails:
        msg = f"User with email {new_user_email} already exists and cannot be created"
        logger.info(msg)
        raise ValidationException(msg)
    else:
        logger.info(f'cognito_pre_signup ::: email {new_user_email} is correct')

    return event


def create_db_user(user_id: str, username: str, email: str, phone: str, role: str, company_id: str) -> str:
    logger.info(
          f'create_user_cognito ::: username: {username}, email:{email}, phone: {phone}, user_id: {user_id}'
    )

    user_item = {
        'partkey': users_pk.format(company_id=company_id),
        'sortkey': users_sk.format(user_id=user_id),
        'username': username,
        'id_': user_id,
        'email': email,
        'phone': phone,
        'date_created': datetime.now().isoformat(timespec='seconds'),
        'role': role
    }

    item_cleaned = utils_data.cleanup_dict(user_item, ['n/a', '', ' ', None])
    utils_data.substitute_keys_to_db(item_cleaned)
    resp = get_main_table().put_item(Item=item_cleaned)
    logger.debug(f'create_user_cognito ::: SUCCESS resp: {resp}, items_cleaned: {item_cleaned}')

    return user_id


def create_company_record():
    company_id = str(uuid.uuid4())
    return company_id


def cognito_post_confirmation(event, context):
    try:
        logger.info(f'cognito_post_confirmation ::: triggered: event={event}, context={context}')

        if event.get('triggerSource') == 'PostConfirmation_ConfirmSignUp':
            username = event["userName"]
            attributes = event['request'].get('userAttributes', {})
            role = attributes['custom:role']
            logger.info(f'cognito_post_confirmation ::: {username=}, {attributes=}')

            # u = Cognito(os.environ['COGNITO_POOL_ID'], os.environ['COGNITO_ADMIN_POOL_CLIENT_ID'], username=username)
            # user_groups = u.client.admin_list_groups_for_user(Username=username, UserPoolId=u.user_pool_id)
            #
            # if DEFAULT_GROUP not in user_groups:
            #     logger.info(f'cognito_post_confirmation ::: adding user to group "{DEFAULT_GROUP}"')
            #     u.client.admin_add_user_to_group(UserPoolId=os.environ['COGNITO_POOL_ID'], Username=username,
            #                                      GroupName=DEFAULT_GROUP)

                # logger.info(f'cognito_post_confirmation ::: added user to group "{DEFAULT_GROUP}"')

            if role == 'admin':
                company_id = create_company_record()
                logger.info(f'new company created, {company_id=}')
            else:
                company_id = attributes.get('custom:company_id')
            create_db_user(
                user_id=attributes['sub'],
                username=username,
                email=attributes.get('email', ''),
                phone=attributes.get('phone_number', ''),
                role=role,
                company_id=company_id
            )
        else:
            # If we restore user's password, then you don't create a new user
            pass

    except Exception as e:
        logger.exception(e)
        raise

    return event


def cognito_custom_message(event, context):
    logger.debug(f'cognito_custom_message ::: triggered: event={event}, context={context}')

    email_message = '''
    <img width="200" src="https://restmonster-frontend.s3.eu-central-1.amazonaws.com/restmonster-frontend-assets/logo_t.png"/>
    <br/>
    <p style="white-space: pre-line">Your restaurant manager's account was created.
    Please click the link below to verify your email address.
    {link}</p>
    '''
    logger.debug(f'cognito_custom_message ::: email_message: {email_message}')

    try:
        username = event.get('userName', '')
        code = event['request'].get('codeParameter', '')

        if event['triggerSource'] == "CustomMessage_SignUp":
            # Ensure that your message contains event.request.codeParameter.
            # This is the placeholder for code that will be sent
            client_id = event['callerContext']['clientId']
            user_attr = event['request'].get('userAttributes', {})
            email = event['request'].get('userAttributes', {}).get('email', '')
            url = f'https://api.restmonster.ru/ui/api/signup-confirm/{client_id}/{username}/{code}'
            link = f'<a href="{url}" target="_blank">here</a>'
            event['response']['emailSubject'] = "Your RestMonster verification link"
            event['response']['emailMessage'] = email_message.format(link=link)
            logger.debug(f'cognito_custom_message(): client_id={client_id}, user_attr={user_attr}, email = {email}, url={url}')
            logger.debug(f'cognito_custom_message ::: email_message.format(link)={email_message.format(link=link)}')
        else:
            logger.info(f'cognito_custom_message ::: unhandled event {event["triggerSource"]}')

    except Exception as e:
        logger.exception(f'cognito_custom_message ::: exception: {e}')
        raise e

    return event


def signup_confirmation(client_id, user_name, confirmation_code):
    try:
        logger.debug(f'signup_confirmation ::: {client_id}, {user_name}, {confirmation_code}')

        u = Cognito(os.environ['COGNITO_ADMIN_POOL_ID'], os.environ['COGNITO_ADMIN_POOL_CLIENT_ID'])
        params = {
            'ClientId': client_id,
            'Username': user_name,
            'ConfirmationCode': confirmation_code
        }
        conf_signup_resp = u.client.confirm_sign_up(**params)
        logger.debug(f'signup_confirmation ::: conf_signup_resp: {conf_signup_resp}')
        if conf_signup_resp['ResponseMetadata']['HTTPStatusCode'] == 200:
            resp = Response(
                status_code=302,
                headers={'Location': f'https://restmonster.ru/signupsuccess'},
                body={}
            )
            return resp
        else:
            raise Exception('Not 200 status code')
    except Exception as e:
        logger.exception(e)
        return Response(status_code=302, headers={f'Location': f'https://restmonster.ru/signuperror'}, body={})



# import uuid # for public id
# from werkzeug.security import generate_password_hash, check_password_hash
# # imports for PyJWT authentication
# import jwt
# from datetime import datetime, timedelta
# from functools import wraps
#
# # creates Flask object
# # configuration
# # NEVER HARDCODE YOUR CONFIGURATION IN YOUR CODE
# # INSTEAD CREATE A .env FILE AND STORE IN IT
# app.config['SECRET_KEY'] = 'your secret key'
# # database name
# app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///Database.db'
# app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = True
# # creates SQLALCHEMY object
# db = SQLAlchemy(app)
#
#
# # Database ORMs
# class User(db.Model):
# 	id = db.Column(db.Integer, primary_key = True)
# 	public_id = db.Column(db.String(50), unique = True)
# 	name = db.Column(db.String(100))
# 	email = db.Column(db.String(70), unique = True)
# 	password = db.Column(db.String(80))
#
#
# # decorator for verifying the JWT
# def token_required(f):
# 	@wraps(f)
# 	def decorated(*args, **kwargs):
# 		token = None
# 		# jwt is passed in the request header
# 		if 'x-access-token' in request.headers:
# 			token = request.headers['x-access-token']
# 		# return 401 if token is not passed
# 		if not token:
# 			return jsonify({'message' : 'Token is missing !!'}), 401
#
# 		try:
# 			# decoding the payload to fetch the stored details
# 			data = jwt.decode(token, app.config['SECRET_KEY'])
# 			current_user = User.query\
# 				.filter_by(public_id = data['public_id'])\
# 				.first()
# 		except:
# 			return jsonify({
# 				'message' : 'Token is invalid !!'
# 			}), 401
# 		# returns the current logged in users contex to the routes
# 		return f(current_user, *args, **kwargs)
#
#     return decorated
#
#
# # User Database Route
# # this route sends back list of users
# @app.route('/user', methods =['GET'])
# @token_required
# def get_all_users(current_user):
# 	# querying the database
# 	# for all the entries in it
# 	users = User.query.all()
# 	# converting the query objects
# 	# to list of jsons
# 	output = []
# 	for user in users:
# 		# appending the user data json
# 		# to the response list
# 		output.append({
# 			'public_id': user.public_id,
# 			'name' : user.name,
# 			'email' : user.email
# 		})
#
# 	return jsonify({'users': output})
#
# # route for logging user in
# @app.route('/login', methods =['POST'])
# def login():
# 	# creates dictionary of form data
# 	auth = request.form
#
# 	if not auth or not auth.get('email') or not auth.get('password'):
# 		# returns 401 if any email or / and password is missing
# 		return make_response(
# 			'Could not verify',
# 			401,
# 			{'WWW-Authenticate' : 'Basic realm ="Login required !!"'}
# 		)
#
# 	user = User.query\
# 		.filter_by(email = auth.get('email'))\
# 		.first()
#
# 	if not user:
# 		# returns 401 if user does not exist
# 		return make_response(
# 			'Could not verify',
# 			401,
# 			{'WWW-Authenticate' : 'Basic realm ="User does not exist !!"'}
# 		)
#
# 	if check_password_hash(user.password, auth.get('password')):
# 		# generates the JWT Token
# 		token = jwt.encode({
# 			'public_id': user.public_id,
# 			'exp' : datetime.utcnow() + timedelta(minutes = 30)
# 		}, app.config['SECRET_KEY'])
#
# 		return make_response(jsonify({'token' : token.decode('UTF-8')}), 201)
# 	# returns 403 if password is wrong
# 	return make_response(
# 		'Could not verify',
# 		403,
# 		{'WWW-Authenticate' : 'Basic realm ="Wrong Password !!"'}
# 	)
#
# # signup route
# @app.route('/signup', methods =['POST'])
# def signup():
# 	# creates a dictionary of the form data
# 	data = request.form
#
# 	# gets name, email and password
# 	name, email = data.get('name'), data.get('email')
# 	password = data.get('password')
#
# 	# checking for existing user
# 	user = User.query\
# 		.filter_by(email = email)\
# 		.first()
# 	if not user:
# 		# database ORM object
# 		user = User(
# 			public_id = str(uuid.uuid4()),
# 			name = name,
# 			email = email,
# 			password = generate_password_hash(password)
# 		)
# 		# insert user
# 		db.session.add(user)
# 		db.session.commit()
#
# 		return make_response('Successfully registered.', 201)
# 	else:
# 		# returns 202 if user already exists
# 		return make_response('User already exists. Please Log in.', 202)
#
# if __name__ == "__main__":
# 	# setting debug to True enables hot reload
# 	# and also provides a debugger shell
# 	# if you hit an error while running the server
# 	app.run(debug = True)
