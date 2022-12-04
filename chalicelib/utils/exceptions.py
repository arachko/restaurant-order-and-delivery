__all__ = ["NotAuthorizedException", "AccessDenied", "RecordNotFound", "NumberOfRetriesExceeded",
           "MandatoryFieldsAreNotFilled", "WrongDeliveryAddress", "SomeItemsAreNotAvailable", "OrderNotFound",
           "AuthorizationException"]


class NotAuthorizedException(Exception):
    pass


# Generic Exceptions
class AccessDenied(Exception):
    pass


class MandatoryFieldsAreNotFilled(Exception):
    pass


# DynamoDB exceptions
class RecordNotFound(Exception):
    pass


# DB Performance Exception
class NumberOfRetriesExceeded(Exception):
    pass


# Validations exceptions
class ValidationException(Exception):
    pass


class AuthorizationException(Exception):
    pass


class WrongDeliveryAddress(Exception):
    pass


class SomeItemsAreNotAvailable(Exception):
    pass


class OrderNotFound(Exception):
    pass

