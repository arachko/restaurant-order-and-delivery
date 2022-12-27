import functools
from typing import Callable

from chalice import Response

from chalicelib.utils.exceptions import MandatoryFieldsAreNotFilled, OrderNotFound, AccessDenied
from chalicelib.utils.logger import logger, log_exception


def error_response(error: Exception, msg: str = "", status_code: int = 400, *args, **kwargs):
    log_exception(error=error, msg=msg, status_code=status_code, *args, **kwargs)
    return Response(
        body={
            'error': str(error),
            'exception': error.__class__.__name__,
            "message": str(msg),
            'error_id': getattr(logger, 'current_request_id'),
            'level': getattr(error, 'LEVEL', 'exception')
        },
        status_code=status_code,
        headers={'Content-Type': 'application/json'}
    )


def request_exception_handler(func: Callable):
    @functools.wraps(func)
    def result(*args, **kwargs):
        try:
            logger.info(f'Calling function {func.__name__}')
            return func(*args, **kwargs)
        except MandatoryFieldsAreNotFilled as mandatory_error:
            return error_response(
                error=mandatory_error,
                msg=f'function = {func.__name__} , error = {mandatory_error}',
                status_code=400)
        except OrderNotFound as order_not_found:
            return error_response(
                error=order_not_found,
                msg=f'function = {func.__name__} , error = {order_not_found}',
                status_code=400)
        except AccessDenied as access_denied:
            return error_response(
                error=access_denied,
                msg="You don't have permissions to access this restaurant",
                status_code=401)
        except Exception as exception:
            return error_response(
                error=exception,
                msg=f'function = {func.__name__}, error = {exception}',
                status_code=500)
    return result


def log_start_finish(func: Callable):
    @functools.wraps(func)
    def result(*args, **kwargs):
        logger.info(f'{func.__name__} ::: started')
        response = func(*args, **kwargs)
        logger.info(f'{func.__name__} ::: finished')
        return response
    return result
