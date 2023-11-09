import json
import sys
import boto3
from datetime import datetime, timezone
from data_functions import *

def lambda_handler(event, context):
    """
    Add GHL message events to dynamodb table as chat history.
    """
    table_name = 'SessionTable' ############
    try:
        if type(event["body"]) == str:
            payload = json.loads(event["body"])
        else:
            payload = event["body"]
            
        message_events = ['InboundMessage', 'OutboundMessage', 'NoteCreate']
        contact_update_events = ['ContactDelete', 'ContactDndUpdate']
        print(f'Payload: {payload}')
        dynamodb = boto3.client('dynamodb') # Initialize DynamoDB client
        if payload['type'] == 'ContactCreate':
            message = add_webhook_data_to_dynamodb(
                payload, table_name, dynamodb
                )
        elif payload['type'] in message_events + contact_update_events:
            # Only save webhook data if contact exists in database so only data from new leads are saved.
            contact_id_key = 'contactId' if payload['type'] in message_events else 'id'
            contact_data = query_dynamodb_table(
                'SessionTable', payload[contact_id_key], key='SessionId'
                )['Items']
            message = add_webhook_data_to_dynamodb(
                payload, table_name, dynamodb
                )
            # if payload['type'] in message_events:
            #     message2 = add_to_chat_history(payload)
            #     message = f'{message}\n{message2}'
            print(message)
        else:
            message = f'No need to save webhook data for {payload["type"]}.'
            print(message)
        return {
            "statusCode": 200,
            "body": json.dumps(message)
        }
    except Exception as error:
        exc_type, exc_obj, tb = sys.exc_info()
        f = tb.tb_frame
        lineno = tb.tb_lineno
        filename = f.f_code.co_filename
        print("An error occurred on line", lineno, "in", filename, ":", error)
        return {
            "statusCode": 500,
            "body": json.dumps(f"Error in line {lineno} of {filename}: {str(error)}")
        }
