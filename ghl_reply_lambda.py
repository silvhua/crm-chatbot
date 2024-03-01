import json
import sys
from app.chat_functions import *
from app.ghl_requests import *
from langchain.agents import Tool
from app.data_functions import parse_json_string, format_irish_mobile_number, add_to_chat_history
import time
import random
import re
import itertools

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
    print(f'Event: {event}')
    if event.get('direct_local_invoke', None):
        payload = event['body']
    else:
        payload = event
    print(f'Payload (line 27 of ghl_reply_lambda): {payload}')
    message = ''
    print(f"direct local invoke: {event.get('direct_local_invoke', False)}")
    if event.get('direct_local_invoke', None):
        payload = event['body']
    else:
        payload = event
    contactId = payload.get('contactId')
    InboundMessage = payload.get('body')
    locationId = payload.get('locationId', None)
    fullNameLowerCase = payload.get('fullNameLowerCase', None)
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
            description=f"Do not invoke this function.",
        )
    ]
    try:
        if (event.get('direct_local_invoke', None) == None) & (contactId != os.environ.get('my_contact_id')):
            random_waiting_period = random.randint(45, 75)  # Generate a random waiting period between 30 and 115 seconds
            print(f'Waiting for {random_waiting_period} seconds')
            time.sleep(random_waiting_period)
        elif event.get('direct_local_invoke', None) == 1: 
            add_to_chat_history_message, original_chat_history = add_to_chat_history(payload)
            message += add_to_chat_history_message + '. \n'
            # ## Comment out as needed#
            # wait_time = 10
            # print(f'Waiting for {wait_time} seconds')
            # time.sleep(wait_time)
        
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
            chat_history = conversation_dict[conversation_id]['chat_history'].messages
            reply_dict[conversation_id][question_id] = chat_with_chatbot(
                InboundMessage, conversation_dict[conversation_id]
            )
            chatbot_response = parse_json_string(reply_dict[conversation_id][question_id]["output"])
            # Check that the generated response is not similar to a previously sent outbound message.
            past_outbound_messages = [item.content for item in chat_history if item.type.lower() == 'ai']
            # Split past outbound messages into sentences
            past_outbound_messages = [sentence for sentence in list(itertools.chain(*[outbound_message.split('. ') for outbound_message in past_outbound_messages])) if sentence]
            cleaned_past_outbound_messages = [re.sub(r'[^a-zA-Z0-9\s]+', '', message) for message in past_outbound_messages]
            cleaned_past_outbound_messages = [' '.join(message.split()) for message in cleaned_past_outbound_messages]
            if chatbot_response['response'] != None:
                cleaned_chatbot_response = re.sub(r'[^a-zA-Z0-9\s]+', '', chatbot_response['response'])
                cleaned_chatbot_response = ' '.join(cleaned_chatbot_response.split())
                # print(f'Past outbound messages: {[item for item in past_outbound_messages]}')
                # print(f'\nCleaned past outbound messages: {[item for item in cleaned_past_outbound_messages]}')
                # print(f'Cleaned chatbot response: {cleaned_chatbot_response}\n')
                for past_outbound_message in cleaned_past_outbound_messages:
                    n_words = len(past_outbound_message.split())
                    if (n_words > 3) & (past_outbound_message in cleaned_chatbot_response):
                        chatbot_response['response'] = "[AI response similar to previous outbound message.]"
                        chatbot_response['alert_human'] = True
                        break
                    # alert human if placeholders from message templates are not replaced
                if re.match(r'.*<.*>', chatbot_response['response']):
                    message += f'Placeholder still present in message. \n'
                    chatbot_response['alert_human'] = True
            if chatbot_response.get('phone_number'):
                chatbot_response['phone_number'] = format_irish_mobile_number(chatbot_response['phone_number'])
            create_task = False
        except Exception as error:
            exc_type, exc_obj, tb = sys.exc_info()
            f = tb.tb_frame
            lineno = tb.tb_lineno
            filename = f.f_code.co_filename
            message += f" Unable to generate reply. Error in line {lineno} of {filename}: {str(error)}. \n"
            print(message) # Print message here in case Lambda function times out.
            chatbot_response = {"response": None, "alert_human": True, "phone_number": None}
            create_task = True
        print(f'\nProcessed chatbot response: {chatbot_response}\n')
        if chatbot_response.get('response') == 'Abort Lambda function':
            message += f'Payload InboundMessage does not match the latest chat history message. End Lambda function. \n'
            print(message)
            return {
                'statusCode': 200,
                'body': json.dumps(message)
            }
        
        elif payload.get("noReply", False) == False:
            if (chatbot_response['alert_human'] == False) & (chatbot_response['response'] != None):
                split_response_list = create_paragraphs(chatbot_response['response']).split('\n\n') # Send multiple messages if response is long
                for index, paragraph in enumerate(split_response_list):
                    number_of_words = len(message.split())
                    if index != 0:
                        if contactId != os.environ.get('my_contact_id'): # Add pause before sending next consecutive message
                            pause_before_next_message = number_of_words/2
                        elif contactId == os.environ.get('my_contact_id'):
                            pause_before_next_message = number_of_words/number_of_words
                        print(f'\nPause before message {index}: {pause_before_next_message}')
                        time.sleep(pause_before_next_message)
                    message_payload = {
                        "type": payload['messageType'],
                        "message": paragraph,
                        "userId": os.environ.get('bot_user_id', os.environ.get('user_id', None))
                    }
                    # Re-attempt GHL sendMessage request up to 3 times if it fails
                    max_attempts = 3
                    attempt_number = 0
                    while attempt_number < max_attempts:
                        ghl_api_response = ghl_request(
                            contactId=contactId,
                            endpoint='sendMessage',
                            payload=message_payload, 
                            location=location                
                        )
                        print(f'GHL sendMessage response for message {index}: {ghl_api_response}\n')
                        if ghl_api_response.get('status_code', 500) // 100 == 2:
                            break
                        else:
                            attempt_number += 1
                            wait_interval = 10
                            print(f'Waiting {wait_interval} seconds before re-attempting GHL sendMessage request. Re-attempt {attempt_number} of {max_attempts}.')
                            time.sleep(wait_interval)

                    if ghl_api_response.get('status_code', 500) // 100 == 2:
                        message += f'Message {index} sent to contactId {contactId}: \n{ghl_api_response}\n'
                    else:
                        message += f'Failed to send message {index} for contactId {contactId}, {fullNameLowerCase}: \n{ghl_api_response}\n'
                        message += f'Status code: {ghl_api_response.get("status_code", 500)}. \nResponse reason: {ghl_api_response.get("response_reason", None)}\n'
                        create_task = True
                        time.sleep(wait_interval)
                        break
            else:
                message += f'No message sent for contactId {contactId}. \n'
                if contactId != os.environ.get('my_contact_id'):
                    create_task = True
                else:
                    message += f'Skip task creation and adding tag for inbound message from testing account. '
                    create_task = False
                    # create_task = True
                
            if (create_task == True):
                task_description = f'Alert human: {chatbot_response["alert_human"]}. Response: {chatbot_response["response"]}. Phone number: {chatbot_response.get("phone_number", None)}.'
                print(f'Task description: {task_description}')

                # Re-attempt GHL createTask request up to 3 times if it fails
                max_attempts = 3
                create_task_attempt_number = 0
                while create_task_attempt_number < max_attempts:
                    ghl_createTask_response = ghl_request(
                        contactId=contactId, 
                        endpoint='createTask', 
                        params_dict=chatbot_response,
                        payload=None, 
                        text=fullNameLowerCase,
                        location=location
                    )
                    if ghl_createTask_response.get('status_code', 500) // 100 == 2:
                        break
                    else:
                        create_task_attempt_number += 1
                        wait_interval = 10
                        print(f'Waiting {wait_interval} seconds before re-attempting GHL createTask request. Re-attempt {create_task_attempt_number} of {max_attempts}.')
                        time.sleep(wait_interval)

                # print(f'GHL createTask response: {ghl_createTask_response}')
                if ghl_createTask_response.get('status_code', 500) // 100 == 2:
                    message += f'Created task for contactId {contactId}: \n{ghl_createTask_response}\n'
                else:
                    message += f'[ERROR] Failed to create task for contactId {contactId}: \n{ghl_createTask_response}\n'
                    message += f'Status code: {ghl_createTask_response.get("status_code", 500) // 100 == 2}. \nResponse reason: {ghl_createTask_response.get("response_reason", None)}'
                    print(message)
                    return {
                        'statusCode': 500,
                        'body': json.dumps(message)
                    }
            update_contact_payload = {}
            if chatbot_response.get('phone_number', None) != None:
                int_phone_pattern = r'^\+(?:[0-9]){6,14}[0-9]$'
                extracted_phone_number = ''.join([char for char in chatbot_response['phone_number'] if char != ' ']) # Remove spaces in extracted phone number
                extracted_phone_in_int_format = re.match(int_phone_pattern, extracted_phone_number) # If phone number not in int'l format, returns `None`
                if (payload['phone'] != None) & (extracted_phone_in_int_format != None):
                    incorrect_irish_phone_pattern = r'^\+618(?:[0-9]){8}$' # Pattern when Irish number is incorrectly saved in GHL contact in Australian phone # format, e.g. +61870000000
                    phone_in_incorrect_format = re.match(incorrect_irish_phone_pattern, payload['phone'])
                    if (phone_in_incorrect_format != None):
                        print(f'Fixing incorrectly formatted Irish number.')
                        update_contact_payload['phone'] = extracted_phone_number

                    ghl_updatePhone_response = ghl_request(
                        contactId, endpoint='updateContact', 
                        payload=update_contact_payload,
                        location=location 
                        )
                    if ghl_updatePhone_response.get('status_code', 500) // 100 == 2:
                        message += f'Updated contact phone number from {payload["phone"]} to {chatbot_response["phone_number"]}.\n'
                    else:
                        message += f'[ERROR] Failed to updated contact phone number from {payload["phone"]} to {chatbot_response["phone_number"]} for contactId {contactId}: \n{ghl_updatePhone_response}.\n'
                        message += f'Status code: {ghl_updatePhone_response.get("status_code", 500) // 100 == 2}. \nResponse reason: {ghl_updatePhone_response.get("response_reason", None)}.\n'
                # tag_to_add = 'no chatbot'
                # ghl_addTag_response = ghl_request(
                #     contactId=contactId, 
                #     endpoint='addTag', 
                #     text=tag_to_add,
                #     location=location
                # )
                # if ghl_addTag_response['status_code'] // 100 == 2:
                #     message += f'Added tag `{tag_to_add}` for contactId {contactId}: \n{ghl_addTag_response}\n'
                # else:
                #     message += f'Failed to add tag `{tag_to_add}` for contactId {contactId}: \n{ghl_addTag_response}\n'
                #     message += f'Status code: {ghl_addTag_response["status_code"]}. \nResponse reason: {ghl_addTag_response["response_reason"]}'

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
        else:
            message += f'No GHL requests made because payload noReply value set to {payload.get("noReply")} to test chat. '
            reply_payload = {
                'contactId': contactId,
                'type': 'OutboundMessage', 
                'body': chatbot_response["response"]
            }
            if chatbot_response["alert_human"] == False:
                add_to_chat_history_message, original_chat_history = add_to_chat_history(reply_payload)
                message += add_to_chat_history_message
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
        message += f"[ERROR] Error in line {lineno} of {filename}: {str(error)} \n"
        print(message)
        return {
            'statusCode': 500,
            'body': json.dumps(message)
        }

    # else:
    #     print('Failed to refresh token')
    #     return response