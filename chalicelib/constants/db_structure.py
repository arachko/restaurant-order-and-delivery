USER = {
    'id_': None,
    'first_name': None,
    'last_name': None,
    'email': None,
    'phone': None,
    'addresses': None,
    'additional_phone_numbers': None,
    'role': None,
    'date_created': None,
    'date_updated': None
}

RESTAURANT = {
    'id_': None,
    'title': None,
    'address': None,
    'description': None,
    'cuisine': None,
    'opening_time': None,
    'closing_time': None,
    'status': None,
    'date_created': None,
    'date_updated': None,
    'created_by': None,
    'updated_by': None,
    'archived': None
}

MENU_ITEM = {
    'id_': None,
    'restaurant_id': None,
    'title': None,
    'description': None,
    'price': None,
    'opening_time': None,
    'closing_time': None,
    'is_available': None,
    'date_created': None,
    'date_updated': None,
    'created_by': None,
    'updated_by': None,
    'archived': None
}

ORDER = {
    'id_': None,
    'user_id': None,
    'restaurant_id': None,
    'items': None,
    'status': None,
    'timeline': {
        'created': None,
        'confirmed': None,
        'ready': None,
        'collected': None,
        'delivered': None,
        'closed': None
    }
}

CART = {
    'user_id': None,
    'restaurant_id': None,
    'items': None
}
