import json
import sys
from app.chat_functions import *
from app.ghl_requests import *
from langchain.agents import Tool
from app.data_functions import parse_json_string, format_irish_mobile_number
import time
import random

try:
    from dotenv import load_dotenv
    load_dotenv()
except Exception as error:
    # exc_type, exc_obj, tb = sys.exc_info()
    # f = tb.tb_frame
    # lineno = tb.tb_lineno
    # filename = f.f_code.co_filename
    # message = f"Error in line {lineno} of {filename}: {str(error)}"
    # print(message)
    pass

def lambda_handler(event, context):
    """
    This Lambda function is triggered by another function when the payload type is 'InboundMessage'.
    """
    if event.get('direct_local_invoke', None):
        payload = event['body']
    else:
        payload = event
    print(f'Payload (line 27 of ghl_reply_lambda): {payload}')
    message = ''
    # response = refresh_token()
    # if response['statusCode'] // 100 == 2:
    # Extract the payload from the event
    print(f"direct local invoke: {event.get('direct_local_invoke', False)}")
    if event.get('direct_local_invoke', None):
        payload = event['body']
    else:
        payload = event
    contactId = payload.get('contactId')
    InboundMessage = payload.get('body')
    locationId = payload.get('locationId', None)
    location = os.getenv(locationId, 'CoachMcloone')
    if location == None:
        message += f'No location found for locationId {locationId}. \n'
        print(message)
        return {
            'statusCode': 500,
            'body': json.dumps(message)
        }
    print(f'location: {location}')

    system_message_dict = dict()
    conversation_dict = dict()
    reply_dict = dict()
    conversation_id = 1
    question_id = 1
    reply_dict[conversation_id] = dict()
    tools = [
        Tool(
            name=f"placeholder_function",
            func=placeholder_function,
            description=f"This function does not do anything.",
        )
    ]
    try:
        if payload.get("noReply", False) == False:
            random_waiting_period = random.randint(30, 115)  # Generate a random waiting period between 30 and 115 seconds
            print(f'Waiting for {random_waiting_period} seconds')
            if event.get('direct_local_invoke', None) == None:
                time.sleep(random_waiting_period)
            try:
                system_message_dict[conversation_id] = create_system_message(
                    'CoachMcloone', 
                    prompts_filepath='app/private/prompts',
                    examples_filepath='app/private/data/chat_examples', doc_filepath='app/private/data/rag_docs'
                )
                conversation_dict[conversation_id] = create_chatbot(
                    contactId, system_message_dict[conversation_id], tools=tools,
                    # model='gpt-4-32k'
                    )

                reply_dict[conversation_id][question_id] = chat_with_chatbot(
                    InboundMessage, conversation_dict[conversation_id]
                )
                chatbot_response = parse_json_string(reply_dict[conversation_id][question_id]["output"])
                if chatbot_response['phone_number']:
                    chatbot_response['phone_number'] = format_irish_mobile_number(chatbot_response['phone_number'])
            except Exception as error:
                exc_type, exc_obj, tb = sys.exc_info()
                f = tb.tb_frame
                lineno = tb.tb_lineno
                filename = f.f_code.co_filename
                message += f" Unable to generate reply. Error in line {lineno} of {filename}: {str(error)}."
                chatbot_response = {"response": None, "alert_human": True, "phone_number": None}
        else:
            chatbot_response = {"response": None, "alert_human": True, "phone_number": None}
        print(f'\nChatbot response: {chatbot_response}\n')
        if (chatbot_response['alert_human'] == False) & (chatbot_response['response'] != None):
            message_payload = {
                "type": payload['messageType'],
                "message": chatbot_response['response']
            }
            ghl_api_response = ghl_request(
                contactId=contactId,
                endpoint='sendMessage',
                payload=message_payload, 
                location=location                
            )
            print(f'GHL createTask response: {ghl_api_response}')
            if ghl_api_response['status_code'] // 100 == 2:
                message += f'Message sent contactId {contactId}: \n{ghl_api_response}\n'
            else:
                message += f'Failed to send message for contactId {contactId}: \n{ghl_api_response}\n'
                message += f'Status code: {ghl_api_response["status_code"]}. \nResponse reason: {ghl_api_response["response_reason"]}'
        else:
            message += f'No message sent for contactId {contactId}. \n'
            if contactId != os.environ.get('my_contact_id'):
                create_task = True
            
        if (create_task == True):
            task_description = f'Alert human: {chatbot_response["alert_human"]}. Response: {chatbot_response["response"]}. Phone number: {chatbot_response["phone_number"]}.'
            print(f'Task description: {task_description}')
            ghl_createTask_response = ghl_request(
                contactId=contactId, 
                endpoint='createTask', 
                params_dict=chatbot_response,
                payload=None, 
                location=location
            )
            # print(f'GHL createTask response: {ghl_createTask_response}')
            if ghl_createTask_response['status_code'] // 100 == 2:
                message += f'Created task for contactId {contactId}: \n{ghl_createTask_response}\n'
            else:
                message += f'Failed to create task for contactId {contactId}: \n{ghl_createTask_response}\n'
                message += f'Status code: {ghl_createTask_response["status_code"]}. \nResponse reason: {ghl_createTask_response["response_reason"]}'
            tag_to_add = 'no chatbot'
            ghl_addTag_response = ghl_request(
                contactId=contactId, 
                endpoint='addTag', 
                text=tag_to_add,
                location=location
            )
            if ghl_addTag_response['status_code'] // 100 == 2:
                message += f'Added tag `{tag_to_add}` for contactId {contactId}: \n{ghl_addTag_response}\n'
            else:
                message += f'Failed to add tag `{tag_to_add}` for contactId {contactId}: \n{ghl_addTag_response}\n'
                message += f'Status code: {ghl_addTag_response["status_code"]}. \nResponse reason: {ghl_addTag_response["response_reason"]}'

        # workflowId = 'ab3df14a-b4a2-495b-86ae-79ab6fad805b'
        # workflowName = 'chatbot:_1-day_follow_up'
        # ghl_workflow_response = ghl_request(
        #     contactId, 'workflow', path_param=workflowId
        # )

        # print(f'GHL workflow response: {ghl_workflow_response}')
        # if ghl_workflow_response['status_code'] // 100 == 2:
        #     message += f'\nAdded contactId {contactId} to "{workflowName}" workflow: \n{ghl_workflow_response}\n'
        # else:
        #     message += f'\nFailed to add contactId {contactId} to "{workflowName} workflow": \n{ghl_workflow_response}\n'
        #     message += f'Status code: {ghl_workflow_response["status_code"]}. \nResponse reason: {ghl_workflow_response["response_reason"]}'
        
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
        message += f"Error in line {lineno} of {filename}: {str(error)}"
        print(message)
        return {
            'statusCode': 500,
            'body': json.dumps(message)
        }

    # else:
    #     print('Failed to refresh token')
    #     return response