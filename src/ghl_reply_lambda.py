import json
import sys
from chat_functions import *
from ghl_requests import *
def lambda_handler(event, context):
    """
    This Lambda function is triggered by another function when the payload type is 'InboundMessage'.
    """
    auth_token_response = json.loads(os.getenv('auth_token_response'))
    print(auth_token_response['SamLab']['access_token'])

    # response = refresh_token()
    # return response
    ## Extract the payload from the event
    # payload = event
    # print(f'Payload: {payload}')
    # contactId = payload.get('contactId')
    # InboundMessage = payload.get('body')
    # locationId = payload.get('locationId', 'SAMLab')
    # location = os.getenv(locationId)

    # system_message_dict = dict()
    # conversation_dict = dict()
    # conversation_id = 1

    # system_message_dict[conversation_id] = create_system_message('SAM_Lab', business_dict)
    # conversation_dict[conversation_id] = create_chatbot(contactId, system_message_dict[conversation_id], tools=tools)

    # reply = chat_with_chatbot(
    #     InboundMessage, conversation_dict[conversation_id]
    # )
    # ghl_api_response = ghl_request(
    #     contactId=contactId, 
    #     text=reply,
    #     endpoint='createTask', 
    #     payload=None, 
    #     location=location
    # )
    # if ghl_api_response['status_code'] // 100 == 2:
    #     message = f'Created task for contactId {contactId}: \n{ghl_api_response}\n'
    # else:
    #     message = f'Failed to create task for contactId {contactId}: \n{ghl_api_response}\n'
    #     message += f'Status code: {ghl_api_response["status_code"]}. \nResponse reason: @{ghl_api_response["response_reason"]}'
    # print(message)
    # return {
    #     'statusCode': 200,
    #     'body': json.dumps(message)
    # }