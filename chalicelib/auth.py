from typing import Dict, Any

from chalice import AuthResponse, AuthRoute
from chalice.app import AuthRequest, ChaliceAuthorizer

from chalicelib.users import User
from chalicelib.utils.auth import get_company_id_by_host
from chalicelib.utils.exceptions import AuthorizationException, RecordNotFound

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
                AuthRoute(path=f'/restaurants', methods=['GET', 'POST']),
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
