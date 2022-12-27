from datetime import datetime
from uuid import uuid4

company_record = {
  "id_": "{company_id}",
  "partkey": "companies_",
  "sortkey": "{company_id}",
}


def get_company_admin_record(company_id):
    user_id = str(uuid4())
    return {
      "partkey": f"users_{company_id}",
      "sortkey": f"{user_id}",
      "role": "company_admin",
      "date_updated": datetime.today().isoformat(timespec='seconds'),
      "company_id": f"{company_id}",
      "id_": f"{user_id}",
      "date_created": datetime.today().isoformat(timespec='seconds'),
      "last_name": "test company_admin last name",
      "login": "+79062358932",
      "additional_phone_numbers": [],
      "phone": "+79062358932",
      "first_name": "test company admin",
      "email": "admin@restcompany.ru"
    }


def get_restaurant_manager_record(company_id, restaurant_ids):
    user_id = str(uuid4())
    return {
      "partkey": f"users_{company_id}",
      "sortkey": f"{user_id}",
      "role": "restaurant_manager",
      "permissions_": {
        "restaurants": {id_: 'all' for id_ in restaurant_ids}
      },
      "date_updated": datetime.today().isoformat(timespec='seconds'),
      "company_id": f"{company_id}",
      "id_": f"{user_id}",
      "date_created": datetime.today().isoformat(timespec='seconds'),
      "last_name": "test rest_manager last name",
      "login": "+79062358932",
      "additional_phone_numbers": [],
      "phone": "+79062358932",
      "first_name": "test restaurant manager",
      "email": "rest.manager@restcompany.ru"
    }


def get_user_record(company_id):
    user_id = str(uuid4())
    return {
      "partkey": f"users_{company_id}",
      "sortkey": f"{user_id}",
      "role": "user",
      "date_updated": datetime.today().isoformat(timespec='seconds'),
      "company_id": f"{company_id}",
      "id_": f"{user_id}",
      "date_created": datetime.today().isoformat(timespec='seconds'),
      "last_name": "test user last name",
      "login": "+79062358932",
      "additional_phone_numbers": [],
      "phone": "+79062358932",
      "first_name": "test user",
      "email": "user@restcompany.ru"
    }
