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
    pass

def lambda_handler(event, context, logger=None):
    """
    This Lambda function is triggered by another function when the payload type is 'InboundMessage'.
    """
    try:
        initialize_messages = []
        if (event.get('direct_local_invoke', False)): # directly from `sam local invoke`
            payload = event['body']
            local_invoke = True
            initialize_messages.append('Directly from `sam local invoke`')
        else: # if from WebhooksLambda, either locally or remotely
            payload = event
            initialize_messages.append('Directly from WebhooksLambda.')
            local_invoke = payload.get('sam_local_invoke', False)
        logging_level = logging.DEBUG if local_invoke else logging.INFO 
        logger = create_function_logger('ghl_reply_lambda', logger, level=logging_level)
        initialize_messages.append(f'Custom_Logger name in Reply Lambda: {logger.logger.name}')
        initialize_messages.append(f'Local invoke: {local_invoke}')
        logger.debug('\n'.join(initialize_messages))
        logger.info(f'Event: {event}')
        message = ''
        ghl_api_response = {}
        # if event.get('direct_local_invoke', None):
        #     payload = event['body']
        # else:
        #     payload = event
        contactId = payload.get('contactId')
        InboundMessage = payload.get('body')
        locationId = payload.get('locationId', None)
        fullNameLowerCase = payload.get('fullNameLowerCase', None)
        location = os.getenv(locationId)
        if location == None:
            message += f'No location found for locationId {locationId}. \n'
            logger.error(message)
            return {
                'statusCode': 500,
                'body': json.dumps(message)
            }
        logger.info(f'location: {location}')

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
        Crm_client = Crm(location) ### Instantiate `Crm` class.
        Crm_client.token = dict()
        Crm_client.token['access_token'] = payload.get('access_token', None)
        if Crm_client.token.get('access_token') == None:
            Crm_client.get_token()
        if (event.get('direct_local_invoke', None) == None) & (contactId != os.environ.get('my_contact_id')):
            random_waiting_period = random.randint(45, 75)  # Generate a random waiting period between 30 and 115 seconds
            logger.debug(f'Waiting for {random_waiting_period} seconds')
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
            chatbot_response = parse_json_string(reply_dict[conversation_id][question_id]["output"], logger=logger)
            # Check that the generated response is not similar to a previously sent outbound message.
            past_messages = [item.content for item in chat_history]
            # Split past outbound messages into sentences
            past_messages = [sentence for sentence in list(itertools.chain(*[re.split(r'[?!.\n]', message) for message in past_messages])) if sentence]
            cleaned_past_messages = [re.sub(r'[^a-zA-Z0-9\s]+', '', message.strip()) for message in past_messages]
            cleaned_past_messages = [''.join(message) for message in cleaned_past_messages]
            logger.debug(f'cleaned_past_messages: {cleaned_past_messages}')
            if chatbot_response['response'] != None:
                cleaned_chatbot_response = re.sub(r'[^a-zA-Z0-9\s]+', '', chatbot_response['response'])
                cleaned_chatbot_response = ' '.join(cleaned_chatbot_response.split())
                logger.debug(f'cleaned_chatbot_response: {cleaned_chatbot_response}')
                for past_outbound_message in cleaned_past_messages:
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
            logger.error(message) # Print message here in case Lambda function times out.
            chatbot_response = {"response": None, "alert_human": True, "phone_number": None}
            create_task = True
        logger.info(f'\nProcessed chatbot response: {chatbot_response}\n')
        if chatbot_response.get('response') == 'Abort Lambda function':
            message += f'Payload InboundMessage does not match the latest chat history message. End Lambda function. \n'
            logger.info(message)
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
                        logger.debug(f'\nPause before message {index}: {pause_before_next_message}')
                        time.sleep(pause_before_next_message)
                    message_payload = {
                        "type": payload['messageType'],
                        "message": paragraph,
                        "userId": os.environ.get('bot_user_id', os.environ.get('user_id', None))
                    }
                    ghl_api_response = Crm_client.send_request_auto_retry(
                        contactId=contactId,
                        endpoint='sendMessage',
                        payload=message_payload, max_attempts=3, wait_interval=15
                    )
                    message += f'GHL sendMessage response for message {index}: {ghl_api_response}\n'
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
                logger.info(f'Task description: {task_description}')

                ghl_createTask_response = Crm_client.send_request_auto_retry(
                    contactId=contactId, 
                    endpoint='createTask', 
                    params_dict=chatbot_response,
                    payload=None, 
                    text=fullNameLowerCase, max_attempts=3, wait_interval=15
                )
            # Add tag(s) to the contact if it is indicated in the chatbot response AND if message was successfully sent.
            ghl_tag_to_add = chatbot_response.get('tag', None)
            if (ghl_tag_to_add != None) & (ghl_tag_to_add not in payload.get('contact_tags', [])) \
                & (ghl_api_response.get('status_code', 500) // 100 == 2):
                ghl_addTag_response = Crm_client.send_request_auto_retry(
                    contactId=contactId, 
                    endpoint='addTag', 
                    text=ghl_tag_to_add, max_attempts=3, wait_interval=15
                )
            elif ghl_tag_to_add in payload.get('contact_tags', []):
                message += f'Tag `{ghl_tag_to_add}` already exists for contact.'
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
        logger.info(message)
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
        logger.error(message)
        return {
            'statusCode': 500,
            'body': json.dumps(message)
        }

    # else:
    #     print('Failed to refresh token')
    #     return response

##### This is not needed because GHl automatically updates phone numbers extracted from chatbot responses.
    
            # update_contact_payload = {}
            # if chatbot_response.get('phone_number', None) != None:
            #     int_phone_pattern = r'^\+(?:[0-9]){6,14}[0-9]$'
            #     extracted_phone_number = ''.join([char for char in chatbot_response['phone_number'] if char != ' ']) # Remove spaces in extracted phone number
            #     extracted_phone_in_int_format = re.match(int_phone_pattern, extracted_phone_number) # If phone number not in int'l format, returns `None`
            #     if (payload['phone'] != None) & (extracted_phone_in_int_format != None):
            #         incorrect_irish_phone_pattern = r'^\+618(?:[0-9]){8}$' # Pattern when Irish number is incorrectly saved in GHL contact in Australian phone # format, e.g. +61870000000
            #         phone_in_incorrect_format = re.match(incorrect_irish_phone_pattern, payload['phone'])
            #         if (phone_in_incorrect_format != None):
            #             print(f'Fixing incorrectly formatted Irish number.')
            #             update_contact_payload['phone'] = extracted_phone_number

            #         ghl_updatePhone_response = ghl_request(
            #             contactId, endpoint='updateContact', 
            #             payload=update_contact_payload,
            #             location=location 
            #             )
            #         if ghl_updatePhone_response.get('status_code', 500) // 100 == 2:
            #             message += f'Updated contact phone number from {payload["phone"]} to {chatbot_response["phone_number"]}.\n'
            #         else:
            #             message += f'[ERROR] Failed to updated contact phone number from {payload["phone"]} to {chatbot_response["phone_number"]} for contactId {contactId}: \n{ghl_updatePhone_response}.\n'
            #             message += f'Status code: {ghl_updatePhone_response.get("status_code", 500) // 100 == 2}. \nResponse reason: {ghl_updatePhone_response.get("response_reason", None)}.\n'
    
    

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