from chalice import Chalice

app = Chalice(app_name='restaurant-menu-and-order')


@app.route('/')
def index():
    return {'hello': 'world'}


@app.route('/users', methods=['POST'])
def create_user():
    user_as_json = app.current_request.json_body
    return {'user': user_as_json}
