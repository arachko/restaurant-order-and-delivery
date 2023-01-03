from boto3.dynamodb.types import TypeDeserializer
from chalice.app import DynamoDBEvent

from chalicelib.orders import db_trigger_order_record
from chalicelib.utils.logger import logger, log_exception


deserializer = TypeDeserializer()

customers_table_trigger_func_dict = {
    'order': db_trigger_order_record
}


def deserialize_ddb_rec(record=None):
    if record is None:
        record = {}
    return {key: deserializer.deserialize(value) for key, value in record.items()}


def db_customers_table_stream_trigger(ddb_event: DynamoDBEvent):
    logger.debug(f'db_customers_table_stream_trigger ::: function triggered ddb_event={ddb_event.to_dict()}')
    for record in ddb_event:
        try:
            normalized_new = deserialize_ddb_rec(record.new_image)
            normalized_old = deserialize_ddb_rec(record.old_image)
            func_key = normalized_new.get('record_type') or normalized_old.get('record_type')
            if func_key in customers_table_trigger_func_dict.keys():
                customers_table_trigger_func_dict[func_key](normalized_old, normalized_new,
                                                            record.event_id, record.event_name)
        except Exception as e:
            log_exception(e)
