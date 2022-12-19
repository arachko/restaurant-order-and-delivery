from boto3.dynamodb.types import TypeDeserializer

from chalicelib.orders import db_trigger_send_order_notification
from chalicelib.utils.logger import logger, log_exception


deserializer = TypeDeserializer()

customers_table_trigger_func_dict = {
    'order': db_trigger_send_order_notification
}


def deserialize_ddb_rec(record):
    return {key: deserializer.deserialize(value) for key, value in record.items()}


def db_customers_table_stream_trigger(event: dict, context: dict):
    logger.debug(f'db_customers_table_stream_trigger ::: function triggered {event=}')
    for record in event.get('Records', []):
        try:
            normalized_new = deserialize_ddb_rec(record['dynamodb'].get('NewImage', {}))
            normalized_old = deserialize_ddb_rec(record['dynamodb'].get('OldImage', {}))
            func_key = normalized_new.get('record_type') or normalized_old.get('record_type')
            if func_key in customers_table_trigger_func_dict.keys():
                customers_table_trigger_func_dict[func_key](normalized_old, normalized_new,
                                                            record['eventID'], record['eventName'])
        except Exception as e:
            log_exception(e)
