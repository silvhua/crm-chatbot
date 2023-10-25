import boto3
from boto3.dynamodb.conditions import Key
import json
from datetime import datetime, timezone

def query_dynamodb_table(table_name, value, key='SessionId', region_name="us-west-2"):
    """
    Query a Dynamodb table and print the results.
    Parameters:
        table_name (str): The name of the DynamoDB table.
        value (str): The value of the key.
        key (str): The name of the key.
        region_name (str): The name of the AWS region.

    Returns:
        dict: The results of the query. The 'Items' key contains the table record.       
    From 2023-10-22 notebook.
    """
    dynamodb = boto3.resource('dynamodb', region_name=region_name)
    table = dynamodb.Table(table_name)
    response = table.query(
        KeyConditionExpression=Key(key).eq(value)
    )
    return response

def add_webhook_data_to_dynamodb(payload, table_name, dynamodb):
    """
    Taken from ghl_webhook_lambda.py
    """
    item_attributes = dict()
    message_events = ['InboundMessage', 'OutboundMessage']
    contact_id_key = 'contactId' if payload['type'] in message_events else 'id'
    item_attributes['SessionId'] = {'S': payload.get(contact_id_key, 'no contact id')}
    payload.pop(contact_id_key)
    message_events = ['InboundMessage', 'OutboundMessage']
    if payload['type'] in message_events:
        item_attributes['type'] = {'S': 'MessageHistory'}
    else:
        item_attributes['type'] = {'S': payload.get('type', 'no event type')}
    payload.pop('type')
    for key, value in payload.items():
        if type(value) == str:
            item_attributes[key] = {'S': value}
        elif type(value) == bool:
            item_attributes[key] = {"BOOL": value}
        elif type(value) == dict:
            item_attributes[key] = {"S": json.dumps(value)}
        elif type(value) == list:
            value = ''.join([f'{item}, ' for item in value])
            item_attributes[key] = {"S": value}
        else:
            print(f'Unable to save payload item {key} of type {type(value)}')
    if payload['type'] in ['ContactDelete', 'ContactDndUpdate']:
        timestamp = datetime.now(timezone.utc).strftime('%Y-%m-%dT%H:%M:%S.%f')[:-3] + 'Z'
        item_attributes['dateAdded'] = {'S': timestamp}
    dynamodb.put_item(
        TableName=table_name,
        Item=item_attributes
    )
    message = f'Data for {payload.get("type", "")} webhook saved to DynamoDB successfully.'
    return message
   