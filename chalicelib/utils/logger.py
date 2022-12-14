import json
import os
from copy import deepcopy
from datetime import datetime, date
from decimal import Decimal
from logging import setLoggerClass, Logger, NOTSET, getLogger, StreamHandler, Formatter
from time import mktime, struct_time

from chalice.app import Request


class CustomLogger(Logger):

    def __init__(self, name, level=NOTSET):
        self.current_request_id = None
        super(CustomLogger, self).__init__(name, level)

    def __change_msg(self, msg):
        return f'[{self.current_request_id}] : {msg}'

    def debug(self, msg, *args, **kwargs):
        super(CustomLogger, self).debug(self.__change_msg(msg), *args, **kwargs)

    def info(self, msg, *args, **kwargs):
        super(CustomLogger, self).info(self.__change_msg(msg), *args, **kwargs)

    def warning(self, msg, *args, **kwargs):
        super(CustomLogger, self).warning(self.__change_msg(msg), *args, **kwargs)

    def error(self, msg, *args, **kwargs):
        super(CustomLogger, self).error(self.__change_msg(msg), *args, **kwargs)

    def log(self, level, msg, *args, **kwargs):
        super(CustomLogger, self).log(level, self.__change_msg(msg), *args, **kwargs)

    def exception(self, msg, *args, exc_info=True, **kwargs):
        super(CustomLogger, self).exception(self.__change_msg(msg), *args, exc_info=exc_info, **kwargs)


def conf_logger(level):
    setLoggerClass(CustomLogger)
    logger_ = getLogger(__name__)
    console_handler = StreamHandler()
    console_handler.setLevel(level)
    formatter = Formatter('%(asctime)s - %(levelname)s - %(message)s')
    console_handler.setFormatter(formatter)
    if logger_.hasHandlers():
        logger_.handlers.clear()
    logger_.addHandler(console_handler)
    logger_.setLevel(level)
    return logger_


logger = conf_logger(os.environ.get('LOG_LEVEL', 'DEBUG').upper())


def log_request(request: Request):
    request_dict = deepcopy(request.to_dict())
    request_dict['headers'].pop('authorization')
    logger.info(f"Request: {json.dumps(request_dict)}")
    if request_dict['headers'].get('content-type', '') == 'application/json':
        logger.debug(f"Request body: {str(request.raw_body)}")


class CustomJSONEncoder(json.JSONEncoder):
    def default(self, value):
        if isinstance(value, datetime):
            return str(value)
        if isinstance(value, date):
            return str(value)
        if isinstance(value, Decimal):
            return float(value)
        if isinstance(value, struct_time):
            return datetime.fromtimestamp(mktime(value))
        # Any other serializer if needed
        return super(CustomJSONEncoder, self).default(value)


def log_exception(error: Exception, status_code: int = 400, msg: str = "", *args, **kwargs):
    allowed_log_levels = {
        'info': logger.info,
        'warning': logger.warning,
        'debug': logger.debug,
        'error': logger.error,
        'exception': logger.exception,
    }
    level = getattr(error, 'LEVEL', 'exception')
    log_level = 'exception' if level not in allowed_log_levels.keys() else level
    allowed_log_levels[log_level](msg=json.dumps({
        'error': str(error),
        'exception': error.__class__.__name__,
        'message': str(msg),
        'level': log_level,
        'status_code': status_code,
        'args': args,
        'kwargs': kwargs
    }, cls=CustomJSONEncoder))


def log_message(*args):
    logger.debug(msg=f'{", ".join([str(i) for i in args])}')
