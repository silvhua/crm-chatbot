import json
import sys
import boto3
from datetime import datetime, timezone
from app.data_functions import *
from app.ghl_requests import *
import os
try:
    from dotenv import load_dotenv
    load_dotenv()
except Exception as error:
    print(f'Did not load .env file: {error}')

def lambda_handler(event, context):
    """
    Add GHL message events to dynamodb table as chat history.
    """
    table_name = 'SessionTable' ############
    message = ''
    try:

        if type(event["body"]) == str:
            payload = json.loads(event["body"])
        else:
            payload = event["body"]
        if (payload['type'] == "OutboundMessage") & (payload.get("messageType", False) == "Email") & ("click here to unsubscribe" in payload.get('body', '').lower()):
            message += f'No need to save webhook data for {payload.get("messageType")} {payload["type"]}. \n'
            print(message)

            return {
                "statusCode": 200,
                "body": json.dumps(message)
            }

        message_events = ['WorkflowInboundMessage', 'InboundMessage', 'OutboundMessage', 'NoteCreate']
        contact_update_events = ['ContactDelete', 'ContactDndUpdate', 'TaskCreate','ContactTagUpdate']
        print(f'Original payload: {payload}')

        if payload.get('workflow'):
            print('Workflow detected')
            if payload['workflow'].get('id', None) == '94af9db9-ac43-4813-b049-8809b49cd48c': # Follow up workflow webhook
            # if payload['workflow'].get('id') == "d453e1aa-8b09-4a52-a105-c9389ab1aa65": # InboundMessages workflow webhook
                payload = transform_webhook(payload)
            print(f'Processed payload: {payload}')
        try:
            dynamodb = boto3.client('dynamodb') # Initialize DynamoDB client
        except:
            aws_access_key_id = os.environ.get('AWS_ACCESS_KEY_ID')
            aws_secret_access_key = os.environ.get('AWS_SECRET_ACCESS_KEY')
            region = os.environ.get('AWS_REGION')
            dynamodb = boto3.client(
                'dynamodb', region_name=region, 
                aws_access_key_id=aws_access_key_id, 
                aws_secret_access_key=aws_secret_access_key
                )
        # payload['type'] = payload.get('type', 'WorkflowInboundMessage')
        # print(f'Payload type: {payload["type"]}')
        if payload['type'] == 'ContactCreate':
            message = add_webhook_data_to_dynamodb(
                payload, table_name, dynamodb
                ) + '. \n'
        elif payload['type'] in message_events + contact_update_events:

            # Only save message_events data if contact exists in database so only data from new leads are saved.
            contact_id_key = 'contactId' if payload['type'] in message_events + ['TaskCreate'] else 'id'
            contact_id = payload[contact_id_key]
            contact_data = query_dynamodb_table(
                'SessionTable', contact_id, partition_key='SessionId'
                )['Items']
            if contact_data: 
                if payload.get("noReply", False) == False:
                    message += add_webhook_data_to_dynamodb(
                        payload, table_name, dynamodb
                        ) + '. \n'
                else:
                    message += 'Testing data not added as new DynamoDB record. \n'
                try:
                    if payload['type'] in message_events:
                        print(f'Webhook type: {payload["type"]}')
                        message += add_to_chat_history(payload) + '. \n'
                        if payload['type'] == 'InboundMessage':
                            # Ignore messages handled by ManyChat workflow
                            messages_to_ignore = [
                                'GET STARTED', '🍎 Nutrition', '💪 Training', '🧠 Knowledge'
                            ]
                            inbound_content = payload.get('body')
                            if inbound_content in messages_to_ignore:
                                message += 'Inbound message handled by ManyChat workflow. \n'
                                location = None
                                actual_location = os.getenv(payload['locationId'])
                            else:
                                location =  os.getenv(payload['locationId'])
                                actual_location = location
                            print(f'Location: {actual_location}') 
                            if location == 'CoachMcloone': ## Update this later to include other businesses
                                try:
                                    refresh_token_response = refresh_token()
                                    if refresh_token_response['statusCode'] == 200:

                                        contact_details = ghl_request(
                                            contact_id, endpoint='getContact', 
                                            location=location 
                                            )
                                        contact_tags = contact_details['contact']['tags']
                                        contact_tags = [tag.strip('"\'') for tag in contact_tags]
                                        print(f'Contact tags: \n{contact_tags}')

                                        if (('money_magnet_lead' in contact_tags) | ('chatgpt' in contact_tags)) and ('money_magnet_schedule' not in contact_tags) \
                                            and ('post comment' not in contact_tags):
                                            # new_payload = {key: payload[key] for key in ['contactId', 'userId', 'body', 'locationId', 'noReply'] if key in payload}
                                            new_payload = payload
                                            # Invoke another Lambda function
                                            if payload.get("noReply", False) == False:
                                                try:
                                                    lambda_client = boto3.client('lambda')  # Initialize Lambda client
                                                except:
                                                    aws_access_key_id = os.environ.get('AWS_ACCESS_KEY_ID')
                                                    aws_secret_access_key = os.environ.get('AWS_SECRET_ACCESS_KEY')
                                                    region = os.environ.get('AWS_REGION')
                                                    lambda_client = boto3.client(
                                                        'lambda', region_name=region, 
                                                        aws_access_key_id=aws_access_key_id, 
                                                        aws_secret_access_key=aws_secret_access_key
                                                        )
                                                lambda_client.invoke(
                                                    FunctionName=os.environ.get('ghl_reply_lambda','ghl-chat-prod-ReplyLambda-9oAzGMbcYxXB'),
                                                    InvocationType='Event',
                                                    Payload=json.dumps(new_payload)
                                                )
                                                message += f'`ghl_reply` Lambda function invoked. \n'
                                            else:
                                                message += f'`ghl_reply` Lambda function skipped because `noReply` is set. \n'
                                        else:
                                            message += f'\nContact is not a relevant lead. No AI response required. \n'
                                    else:
                                        message += f'{message}\n{refresh_token_response["body"]}. \n'

                                except Exception as error:
                                    exc_type, exc_obj, tb = sys.exc_info()
                                    f = tb.tb_frame
                                    lineno = tb.tb_lineno
                                    filename = f.f_code.co_filename
                                    message += f'Error getting contact details. An error occurred on line {lineno} in {filename}: {error}. \n'
                            else:
                                message += f'Location set to {location}; ghl_reply skipped. \n'
                        else:
                            message += f'Not an inbound message; ghl_reply skipped. \n'
                except Exception as error:
                    exc_type, exc_obj, tb = sys.exc_info()
                    f = tb.tb_frame
                    lineno = tb.tb_lineno
                    filename = f.f_code.co_filename
                    message2 = f'An error occurred on line {lineno} in {filename}: {error}.'
                    message = f'{message}\n{message2}'
            else:
                message = f'Contact not in database. No need to save for webhook type {payload["type"]}. \n'

        elif payload['type'] == "Workflow":
            try:
                lambda_client = boto3.client('lambda')  # Initialize Lambda client
            except:
                aws_access_key_id = os.environ.get('AWS_ACCESS_KEY_ID')
                aws_secret_access_key = os.environ.get('AWS_SECRET_ACCESS_KEY')
                region = os.environ.get('AWS_REGION')
                lambda_client = boto3.client(
                    'lambda', region_name=region, 
                    aws_access_key_id=aws_access_key_id, 
                    aws_secret_access_key=aws_secret_access_key
                    )
            lambda_client.invoke(
                FunctionName=os.environ.get('ghl_followup_lambda','ghl-chat-prod-FollowupLambda-EilvE9Mq3fKg'),
                InvocationType='Event',
                Payload=json.dumps(payload)
            )
            message += f'`ghl_followup` Lambda function invoked. \n'
        else:
            message += f'No need to save webhook data for {payload["type"]}. \n'
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
