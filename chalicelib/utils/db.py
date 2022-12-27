import functools
import os
from random import uniform

import boto3 as boto3

from chalicelib.constants import substitute_keys
from chalicelib.utils import data
from chalicelib.utils import exceptions
from chalicelib.utils.boto_clients import aws_config_ddb
from chalicelib.utils.logger import logger, log_exception

# For safe db operations
RETRY_EXCEPTIONS = ('ProvisionedThroughputExceededException', 'ThrottlingException')
need_return_capacity = ('put_item', 'get_item', 'update_item', 'delete_item')

_DB = None


def exp_db_backoff(func):
    """
        should be used for any atomic
        get/put item in the code
    """

    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        logger.debug(f'{func.__name__}:: args={args}, kwargs={kwargs}')
        max_retries = 15
        timeout_seed = uniform(0.1, 0.99)

        for retries in range(max_retries):
            try:
                if func.__name__ in need_return_capacity:
                    kwargs.update({'ReturnConsumedCapacity': 'TOTAL'})
                else:
                    raise RuntimeError("This decorator only for DynamoDB methods")
                result = func(*args, **kwargs)
                logger.info(f'{func.__name__}:: SUCCESS')

                return result

            except Exception as e:
                log_exception(e, msg=f'Got exception while trying to {func.__name__}: ')
                raise

        raise exceptions.NumberOfRetriesExceeded(
            f"MaxNumber={max_retries} of DB retries has exceeded"
        )

    return wrapper


def get_table(gl_table: boto3.session.Session.resource, table_name: str) -> boto3.session.Session.resource:
    if gl_table is None:
        if os.environ.get('ENDPOINT_URL'):
            gl_table = boto3.resource('dynamodb', endpoint_url=os.environ.get('ENDPOINT_URL')).Table(table_name)
        else:
            gl_table = boto3.resource('dynamodb', config=aws_config_ddb).Table(table_name)

        gl_table.put_item = exp_db_backoff(gl_table.put_item)
        gl_table.get_item = exp_db_backoff(gl_table.get_item)
        gl_table.update_item = exp_db_backoff(gl_table.update_item)
        gl_table.delete_item = exp_db_backoff(gl_table.delete_item)

    return gl_table


def get_gen_table():
    return get_table(_DB, os.environ.get('GEN_TABLE_NAME'))


def put_db_record(item: dict, table=get_gen_table):
    table().put_item(Item=item)


def update_db_record(key: dict, update_body: dict, allowed_attrs_to_update: list,
                     allowed_attrs_to_delete: list, table=get_gen_table):
    data.substitute_keys(dict_to_process=update_body, base_keys=substitute_keys.to_db)
    set_expr, expr_attr_values, remove_expr = generate_update_expression(
        update_body=update_body,
        allowed_attrs_to_update=allowed_attrs_to_update,
        allowed_attrs_to_delete=allowed_attrs_to_delete
    )
    update_item_dict = {"Key": key, "ReturnValues": "UPDATED_NEW", }

    set_response = None
    if set_expr:
        set_item_dict = {
            **update_item_dict,
            "UpdateExpression": set_expr,
            "ExpressionAttributeValues": expr_attr_values
        }
        set_response = table().update_item(**set_item_dict)

    remove_response = None
    if remove_expr:
        remove_item_dict = {
            **update_item_dict,
            "UpdateExpression": remove_expr
        }
        remove_response = table().update_item(**remove_item_dict)

    return set_response, remove_response


def generate_update_expression(update_body: dict, allowed_attrs_to_update: list, allowed_attrs_to_delete: list):
    """
    Generate expressions to update and delete attributes.
    if a key of update_body is empty - the attribute is deleted, else - attribute is updated
    """
    expr_attr_values = {}
    set_expr = 'SET '
    remove_expr = 'REMOVE '
    return_value = [None, None, None]
    for field in allowed_attrs_to_update:
        field_value = update_body.get(field, None)
        if field_value is not None:
            # if field is in update_body but is equal to empty string, list etc. - delete field
            if field_value in ['', [], {}] and field in allowed_attrs_to_delete:
                remove_expr += f'{field}, '
            else:
                # if field is in update_body and has a real value - update field
                expr_attr_values[f':{field}'] = update_body.get(field)
                set_expr += f'{field}=:{field}, '
        else:
            continue

    if set_expr != 'SET ':
        return_value[0] = set_expr[:-2]
        return_value[1] = expr_attr_values

    if remove_expr != 'REMOVE ':
        return_value[2] = remove_expr[:-2]

    return return_value


def get_db_item(partkey, sortkey, table=get_gen_table):
    result = table().get_item(
        Key={
            'partkey': partkey,
            'sortkey': sortkey
        }
    )

    if result.__contains__('Item'):
        return result['Item']
    else:
        logger.error(f"get_db_item ::: record partkey={partkey} sortkey={sortkey} not found")
        raise exceptions.RecordNotFound(f'record partkey={partkey} sortkey={sortkey} not found')


def query_items_paginated(
        key_condition_expression,
        filter_expression=None,
        projection_expression=None,
        table=get_gen_table,
        index_name=None,
        expr_attr_names=None,
        limit=None,
        start_key=None
):
    kwargs = {'KeyConditionExpression': key_condition_expression}
    if filter_expression:
        kwargs.update({'FilterExpression': filter_expression})

    if projection_expression:
        kwargs.update({'ProjectionExpression': projection_expression})

    if expr_attr_names:
        kwargs.update({'ExpressionAttributeNames': expr_attr_names})

    if limit:
        kwargs.update({'Limit': int(limit)})

    if index_name:
        kwargs.update({'IndexName': index_name})

    if start_key:
        kwargs.update({'ExclusiveStartKey': start_key})

    resp = table().query(**kwargs)
    return resp['Items'], resp.get('LastEvaluatedKey')


def query_items_paged(key_condition_expression, filter_expression=None, projection_expression=None,
                      table=get_gen_table, index_name=None, expr_attr_names=None):
    """ This method shall be used whenever you think the query will
        return more than 1mb of data at once"""
    all_items = []
    items, last_evaluated_key = query_items_paginated(
        key_condition_expression,
        filter_expression=filter_expression,
        projection_expression=projection_expression,
        table=table,
        index_name=index_name,
        expr_attr_names=expr_attr_names
    )
    all_items.extend(items)

    while last_evaluated_key is not None:
        items, last_evaluated_key = query_items_paginated(
            key_condition_expression,
            filter_expression=filter_expression,
            projection_expression=projection_expression,
            table=table,
            index_name=index_name,
            expr_attr_names=expr_attr_names,
            start_key=last_evaluated_key
        )
        all_items.extend(items)

    return all_items
