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
        if (payload['type'] == "OutboundMessage") & (payload.get("messageType", False) == "Email") & \
            (("click here to unsubscribe" in payload.get('body', '').lower()) | ("unsubscribe here</a>" in payload.get('body', '').lower())):
            message += f'No need to save webhook data for {payload.get("messageType")} {payload["type"]}. \n'
            print(message)

            return {
                "statusCode": 200,
                "body": json.dumps(message)
            }
        message_events = ['WorkflowInboundMessage', 'InboundMessage', 'OutboundMessage', 'NoteCreate']
        contact_update_events = ['ContactDelete', 'ContactDndUpdate', 'TaskCreate','ContactTagUpdate']
        print(f'Original payload: {payload}')
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
        if payload['type'] == 'ContactCreate':
            message = add_webhook_data_to_dynamodb(
                payload, table_name, dynamodb
                ) + ' \n'
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
                        ) + ' \n'
                else:
                    message += 'Testing data not added as new DynamoDB record. \n'
                try:
                    location = os.getenv(payload['locationId'])
                    print(f'Location: {location}')
                    if payload['type'] in message_events:
                        print(f'Webhook type: {payload["type"]}')
                        add_to_chat_history_message, original_chat_history = add_to_chat_history(payload)
                        message += add_to_chat_history_message + '. \n'
                        print(f'Original chat history: {original_chat_history} \n')
                        if (payload['type'] == 'InboundMessage'):
                            try:
                                refresh_token_response = refresh_token()
                                if refresh_token_response['statusCode'] == 200:
                                    inbound_content = payload.get('body')
                                    manychat_optin_messages = ['GET STARTED', 'Get Started']
                                    past_inbound_messages = [item.content for item in original_chat_history if item.type.lower() == 'human']
                                    create_task = False
                                    # If past inbound messages contain the ManyChat opt-in message, add tag and create task; do not invoke Reply Lambda
                                    repeated_optin_messages = set(manychat_optin_messages).intersection(set(past_inbound_messages))
                                    # print(f'Repeated opt-in messages: {repeated_optin_messages}.')
                                    if (inbound_content in manychat_optin_messages) & (len(repeated_optin_messages) > 0): 
                                        ghl_tag_to_add = ['re-entered ManyChat funnel', 'no chatbot']
                                        create_task = True
                                        contact_tags = ghl_tag_to_add
                                        message += f'ghl_reply` Lambda function skipped because contact has previously entered ManyChat funnel. \n'
                                    else:
                                        contact_details = ghl_request(
                                            contact_id, endpoint='getContact', 
                                            location=location 
                                            )
                                        contact_tags = contact_details['contact']['tags']
                                        contact_tags = [tag.strip('"\'') for tag in contact_tags]
                                        print(f'GHL contact tags: \n{contact_tags}')
                                        # contact_fullname = f"{contact_details['contact']['firstName']} {contact_details['contact']['lastName']}"
                                        tags_for_human = [ # If contact has any of these GHL tags, ghl_reply Lambda wont' be invoked and task will be created to notify human
                                            'no chatbot',
                                            'money_magnet_schedule'
                                        ]
                                        messages_to_ignore = manychat_optin_messages + [ # messages handled by ManyChat workflow
                                            '🍎 Nutrition', '💪 Training', '🧠 Knowledge'
                                        ] 
                                        ghl_tag_to_add = None
                                        if inbound_content in messages_to_ignore:
                                            message += 'Inbound message handled by ManyChat workflow. \n'
                                            ghl_tag_to_add = ['facebook lead', 'chatgpt'] if inbound_content.lower() == 'get started' else 'no height and weight'
                                        # elif ('money_magnet_lead' in contact_manychat_tags) | ('money_magnet_lead' in contact_tags) | ('chatgpt' in contact_tags):
                                        elif ('money_magnet_lead' in contact_tags) | ('chatgpt' in contact_tags):
                                            if (len(set(contact_tags).intersection(set(tags_for_human))) == 0):
                                                new_payload = payload
                                                new_payload['contact_tags'] = contact_tags
                                                new_payload['phone'] = contact_details['contact'].get('phone', None)
                                                new_payload['fullNameLowerCase'] = contact_details['contact'].get('fullNameLowerCase', None)
                                                # new_payload['email'] = payload['contact'].get('email', None)
                                                # print(f'New payload: \n{new_payload}')
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
                                                create_task = True
                                                message += f'`ghl_reply` Lambda function skipped based on contact tags. \n'
                                        else:
                                            message += f'\nContact is not a relevant lead. No AI response required. \n'
                                    if 'no height and weight' in contact_tags:
                                        ## Remove from manychat follow up workflow.
                                        workflowId = 'f6072b18-9c34-4a36-9683-f77c9a0fd401'
                                        workflowName = 'silvia: manychat followup'
                                        ghl_workflow_response = ghl_request(
                                            contact_id, 'removeFromWorkflow', path_param=workflowId
                                        )
                                        print(f'GHL workflow response: {ghl_workflow_response}')
                                        if ghl_workflow_response['status_code'] // 100 == 2:
                                            message += f'\nRemoved contactId {contact_id} from "{workflowName}" workflow: \n{ghl_workflow_response}\n'
                                        else:
                                            message += f'\nFailed to Remove contactId {contact_id} from "{workflowName} workflow": \n{ghl_workflow_response}\n'
                                            message += f'Status code: {ghl_workflow_response["status_code"]}. \nResponse reason: {ghl_workflow_response["response_reason"]}'
                                        ghl_tag_to_remove = 'no height and weight'
                                        ghl_removeTag_response = ghl_request(
                                            contactId=contact_id, 
                                            endpoint='removeTag', 
                                            text=ghl_tag_to_remove,
                                            location=location
                                        )
                                        if ghl_removeTag_response['status_code'] // 100 == 2:
                                            message += f'Removed tag `{ghl_tag_to_remove}` for contactId {contact_id}: \n{ghl_removeTag_response}\n'
                                        else:
                                            message += f'Failed to Remove tag `{ghl_tag_to_remove}` for contactId {contact_id}: \n{ghl_removeTag_response}\n'
                                            message += f'Status code: {ghl_removeTag_response["status_code"]}. \nResponse reason: {ghl_removeTag_response["response_reason"]}'
                                    if ghl_tag_to_add != None:
                                        # message += f'Adding GHL tag "{ghl_tag_to_add}" to contact... \n'
                                        ghl_addTag_response = ghl_request(
                                            contactId=contact_id, 
                                            endpoint='addTag', 
                                            text=ghl_tag_to_add,
                                            location=location
                                        )
                                        if ghl_addTag_response['status_code'] // 100 == 2:
                                            message += f'Added tag `{ghl_tag_to_add}` for contactId {contact_id}: \n{ghl_addTag_response}\n'
                                        else:
                                            message += f'Failed to add tag `{ghl_tag_to_add}` for contactId {contact_id}: \n{ghl_addTag_response}\n'
                                            message += f'Status code: {ghl_addTag_response["status_code"]}. \nResponse reason: {ghl_addTag_response["response_reason"]}'
                                    if create_task == True:
                                        if contact_id != os.environ.get('my_contact_id', ''):
                                            task_body = 'Contact tags: ' + ', '.join([tag for tag in contact_tags])
                                            ghl_createTask_response = ghl_request(
                                                contactId=contact_id, 
                                                endpoint='createTask', 
                                                text=task_body, 
                                                params_dict=None,
                                                payload=None, 
                                                location=location
                                            )
                                            # print(f'GHL createTask response: {ghl_createTask_response}')
                                            if ghl_createTask_response['status_code'] // 100 == 2:
                                                message += f'Created respond task for contactId {contact_id}: \n{ghl_createTask_response}\n'
                                            else:
                                                message += f'Failed to create respond task for contactId {contact_id}: \n{ghl_createTask_response}\n'
                                                message += f'Status code: {ghl_createTask_response["status_code"]}. \nResponse reason: {ghl_createTask_response["response_reason"]}'
                                        else:
                                            message += f'Skip task creation and adding tag for inbound message from testing account. '
                                else:
                                    message += f'{message}\n{refresh_token_response["body"]}. \n'
                            except Exception as error:
                                exc_type, exc_obj, tb = sys.exc_info()
                                f = tb.tb_frame
                                lineno = tb.tb_lineno
                                filename = f.f_code.co_filename
                                message += f'Error getting contact details. An error occurred on line {lineno} in {filename}: {error}. \n'
                        else:
                            message += f'Not an inbound message; ghl_reply skipped. \n'
                except Exception as error:
                    exc_type, exc_obj, tb = sys.exc_info()
                    f = tb.tb_frame
                    lineno = tb.tb_lineno
                    filename = f.f_code.co_filename
                    message += f'An error occurred on line {lineno} in {filename}: {error}.'
            else:
                message += f'Contact not in database. No need to save for webhook type {payload["type"]}. \n'

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
        
        print(f'\nOriginal payload: {payload}\n')
        return {
            "statusCode": 500,
            "body": json.dumps(f"Error in line {lineno} of {filename}: {str(error)}")
        }
                                        # try:
                                        #     manychat_contact_details = manychat_request(contact_fullname)
                                        #     contact_manychat_tags = manychat_tags(manychat_contact_details) # tags are listed in reverse chronological order of when they are added
                                        #     print(f'ManyChat contact tags: \n{contact_manychat_tags}')
                                        # except:
                                        #     manychat_contact_details = None
                                        #     contact_manychat_tags = []
                                        #     print('Failed to get ManyChat contact details. \n')

                                        
                                        # elif (len(contact_tags) == 0) & (manychat_contact_details == None):
                                        #     message += f'\nUnable to retrieve ManyChat details. \n'
                                        #     task_payload = {
                                        #         'title': 'Inbound message received but Chatbot is unable to get ManyChat contact details.',
                                        #         'body': f'No GHL tags found. Add tag "chatgpt" to activate chatbot for contact, or "no chatbot" to circumvent chatbot.',
                                        #         'assignedTo': os.environ['user_id']
                                        #     }
                                        #     ghl_createTask_response = ghl_request(
                                        #         contactId=contact_id, 
                                        #         endpoint='createTask', 
                                        #         text=None, 
                                        #         params_dict=None,
                                        #         payload=task_payload, 
                                        #         location=location
                                        #     )
                                        #     if ghl_createTask_response['status_code'] // 100 == 2:
                                        #         message += f'Created notification task for contactId {contact_id}: \n{ghl_createTask_response}\n'
                                        #     else:
                                        #         message += f'Failed to create notification task for contactId {contact_id}: \n{ghl_createTask_response}\n'
                                        #         message += f'Status code: {ghl_createTask_response["status_code"]}. \nResponse reason: {ghl_createTask_response["response_reason"]}'
