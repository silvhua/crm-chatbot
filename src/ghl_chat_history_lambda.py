import json
import sys
import boto3
from datetime import datetime, timezone
from data_functions import *

def lambda_handler(event, context):
    """
    Add GHL message events to dynamodb table as chat history.
    """
    try:
        if type(event["body"]) == str:
            payload = json.loads(event["body"])
        else:
            payload = event["body"]
            
        message_events = ['InboundMessage', 'OutboundMessage']
        print(f'Payload: {payload}')
        if payload['type'] in message_events :
            table_name = 'ghlWebhooks' ############
            dynamodb = boto3.client('dynamodb') # Initialize DynamoDB client
            contact_data = query_dynamodb_table(
                'SessionTable', payload['contactId'], key='SessionId'
                )['Items']
            if len(contact_data) == 0:
                message = add_webhook_data_to_dynamodb(
                    payload, table_name, dynamodb, chat=True
                    )
            else:
                pass
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
