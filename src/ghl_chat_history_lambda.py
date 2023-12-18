import json
import sys
import boto3
from datetime import datetime, timezone
from app.data_functions import *
from app.ghl_requests import *

def lambda_handler(event, context):
    """
    Add GHL message events to dynamodb table as chat history.
    """
    print(f'System paths: {sys.path}')
    table_name = 'SessionTable' ############
    try:
        if type(event["body"]) == str:
            payload = json.loads(event["body"])
        else:
            payload = event["body"]
            
        message_events = ['InboundMessage', 'OutboundMessage', 'NoteCreate']
        contact_update_events = ['ContactDelete', 'ContactDndUpdate', 'TaskCreate','ContactTagUpdate']
        print(f'Payload: {payload}')
        dynamodb = boto3.client('dynamodb') # Initialize DynamoDB client
        if payload['type'] == 'ContactCreate':
            message = add_webhook_data_to_dynamodb(
                payload, table_name, dynamodb
                )
        elif payload['type'] in message_events + contact_update_events:
            # Only save message_events data if contact exists in database so only data from new leads are saved.
            contact_id_key = 'contactId' if payload['type'] in message_events + ['TaskCreate'] else 'id'
            contact_id = payload[contact_id_key]
            contact_data = query_dynamodb_table(
                'SessionTable', contact_id, partition_key='SessionId'
                )['Items']
            if contact_data: 
                if payload.get("noReply", False) == False:
                    message = add_webhook_data_to_dynamodb(
                        payload, table_name, dynamodb
                        )
                else:
                    message = 'Testing data not added to DynamoDB.'
                try:
                    if payload['type'] in message_events:
                        # if (payload['type'] != 'InboundMessage'):
                        print(f'Webhook type: {payload["type"]}')
                        message2 = add_to_chat_history(payload)
                        message = f'{message}\n{message2}'
                        if payload['type'] == 'InboundMessage':
                            location =  os.getenv(payload['locationId'])
                            print(f'Location: {location}') 
                            if location == 'SAM Lab': ## Update this later to include other businesses
                                try:
                                    contact_details = ghl_request(
                                        contact_id, endpoint='getContact', 
                                        location=convert_to_pascal_case(location) ## Update this later to include other businesses
                                        )
                                    contact_tags = contact_details['contact']['tags']
                                    contact_tags = [tag.strip('"\'') for tag in contact_tags]
                                    print(f'Contact tags: \n{contact_tags}')

                                    if 'sam lab members' not in contact_tags:
                                        new_payload = {key: payload[key] for key in ['contactId', 'userId', 'body', 'locationId', 'noReply'] if key in payload}
                                        # Invoke another Lambda function
                                        if payload.get("noReply", False) == False:
                                            lambda_client = boto3.client('lambda')  # Initialize Lambda client
                                            lambda_client.invoke(
                                                FunctionName='ghl_reply',
                                                InvocationType='Event',
                                                Payload=json.dumps(new_payload)
                                            )
                                            message3 = f'`ghl_reply` function invoked.'
                                            message = f'{message}\n{message3}'
                                        else:
                                            message3 = f'`ghl_reply` function skipped because `noReply` is set.'
                                            message = f'{message}\n{message3}'
                                    else:
                                        print(f'Contact is a already member. No AI response required.')
                                except:
                                    print(f'Error getting contact details.')
                            # else:
                            #     print(f'Webhook type: {payload["type"]} for other location')
                            #     message2 = add_to_chat_history(payload)
                            #     message = f'{message}\n{message2}'

                except Exception as error:
                    exc_type, exc_obj, tb = sys.exc_info()
                    f = tb.tb_frame
                    lineno = tb.tb_lineno
                    filename = f.f_code.co_filename
                    message2 = f'An error occurred on line {lineno} in {filename}: {error}.'
                    message = f'{message}\n{message2}'
            else:
                message = f'Contact not in database. No need to save for webhook type {payload["type"]}.'
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
