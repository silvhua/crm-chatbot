import json
import sys
from app.ghl_requests import *
from app.data_functions import *
try:
    from dotenv import load_dotenv
    load_dotenv()
except Exception as error:
    pass

def lambda_handler(event, context):
    """
    This Lambda function is triggered by another function when the payload type is 'Workflow'.
    """
    if event.get('direct_local_invoke', None):
        payload = event['body'] 
    else:
        payload = event
    print(f'Payload: {payload}')
    message = ''
    # response = refresh_token() ##########
    response = {'statusCode': 200, 'body': 'Success'}
    if response['statusCode'] // 100 == 2:
        # Extract the payload from the event
        print(f"direct local invoke: {event.get('direct_local_invoke', False)}")
        if event.get('direct_local_invoke', None):
            payload = event['body']
        else:
            payload = event
        try:
            contactId = payload.get('contactId')
        except:
            contactId = payload.get('contact_id')
        print(f'contactId: {contactId}')
        try:
            workflow_id = payload.get('workflowId')
            workflow_name = payload.get('workflowName')
        except:
            workflow_id = payload['workflow'].get('id')
            workflow_name = payload['workflow'].get('name')
        print(f'workflow_id: {workflow_id}, workflow_name: {workflow_name}')
        if workflow_id == '94af9db9-ac43-4813-b049-8809b49cd48c': # Follow up workflow webhook
            message_text = 'Hi!'
            query_dynamodb_response = query_dynamodb_table(
                table_name='SessionTable', 
                partition_key_value=contactId, partition_key='SessionId',
                sort_key_value='lastInboundMessage', sort_key='type'
            )
            print(f'query_dynamodb_response: {query_dynamodb_response}')
            try:
                message_payload = {
                    'type': query_dynamodb_response['Items'][0]['messageType'],
                    'message': message_text
                }
                ghl_api_response = ghl_request(
                    contactId=contactId, 
                    endpoint='sendMessage', 
                    payload=message_payload
                )
                print(f'GHL Add Contact to Workflow response: {ghl_api_response}')
                if ghl_api_response['status_code'] // 100 == 2:
                    message = f'Sent message to contactId {contactId}: \n{message_text}\n'
                else:
                    message = f'Failed to send message to contactId {contactId} to workflow: \n{ghl_api_response}\n'
                    message += f'Status code: {ghl_api_response["status_code"]}. \nResponse reason: {ghl_api_response["response_reason"]}'
                
                print(message)
                return {
                    'statusCode': 200,
                    'body': json.dumps(message)
                }
            except Exception as error:
                exc_type, exc_obj, tb = sys.exc_info()
                f = tb.tb_frame
                lineno = tb.tb_lineno
                filename = f.f_code.co_filename
                message = f"Error in line {lineno} of {filename}: {str(error)}"
                print(message)
                return {
                    'statusCode': 500,
                    'body': json.dumps(message)
                }

    else:
        print('Failed to refresh token')
        return response