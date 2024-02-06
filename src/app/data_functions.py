import boto3
from boto3.dynamodb.conditions import Key
import json
from datetime import datetime, timezone
import sys
import os
import re

def parse_json_string(json_string, dict_keys=['response', 'alert_human', 'phone_number']):
    """
    Parses the result from Open AI response and returns a dictionary that matches the specified dictionary keys.
    
    Parameters:
        - json_string (str): The JSON string to parse.
        - dict_keys (list): A list of dictionary keys that should be present in the parsed dictionary.
    
    Returns:
        - dict: The parsed dictionary that matches the specified dictionary keys.
    
    Raises:
        - Exception: If there is an error while parsing the JSON string.
    """
    try:
        parsed_json = json.loads(json_string)
        
        if isinstance(parsed_json, list):
            parsed_dict = {}
            for item in reversed(parsed_json):
                if isinstance(item, dict) and all(key in item for key in dict_keys):
                    parsed_dict = item
                    break
            if parsed_dict:
                return parsed_dict
        
        return parsed_json
    
    except Exception as error:
        exc_type, exc_obj, tb = sys.exc_info()
        f = tb.tb_frame
        lineno = tb.tb_lineno
        filename = f.f_code.co_filename
        message = f" Unable to parse JSON string: Line {lineno} of {filename}: {str(error)}."
        print(message)
        
        # Extract substring matching the format of a json string
        regex = r'({[^{}]+})'
        matches = re.findall(regex, json_string)
        
        parsed_dict = {}
        
        for match in reversed(matches):
            temp_dict = json.loads(match)
            if all(key in temp_dict for key in dict_keys):
                parsed_dict = temp_dict
                break
        
        if parsed_dict:
            return parsed_dict
        else:
            print(f'Unparsed JSON string: \n{json_string}')
            return {"response": None, "alert_human": True}

def query_dynamodb_table(
    table_name, partition_key_value, sort_key_value='', partition_key='SessionId', sort_key=None, 
    profile=None, region_name="us-west-2"
    ):
    """
    Query a Dynamodb table based on both the partition key and sort key.
    Parameters:
        table_name (str): The name of the DynamoDB table.
        partition_key_value (str): The value of the partition key.
        sort_key_value (str): The value of the sort key.
        partition_key (str): The name of the partition key.
        sort_key (str): The name of the sort key.
        region_name (str): The name of the AWS region.

    Returns:
        dict: The results of the query. The 'Items' key contains the table record.       
    From 2023-10-22 notebook.
    """
    if profile:
        session = boto3.Session(profile_name=profile)
        dynamodb = session.resource('dynamodb', region_name=region_name)
    else:
        dynamodb = boto3.resource('dynamodb', region_name=region_name)
    table = dynamodb.Table(table_name)
    if sort_key:
        KeyConditionExpression = Key(partition_key).eq(partition_key_value) & Key(sort_key).eq(sort_key_value)
    else:
        KeyConditionExpression = Key(partition_key).eq(partition_key_value)
    # print(f'KeyConditionExpression: {KeyConditionExpression}')
    response = table.query(
        KeyConditionExpression=KeyConditionExpression,
    )
    return response

def transform_webhook(payload):
    """
    Generate the processed webhook from the given payload so it works with `add_webhook_data_to_dynamodb` function.

    Args:
        payload (dict): The payload received from the webhook.

    Returns:
        dict: The processed webhook dictionary.

    Raises:
        None
    """
    processed_webhook = dict()
    processed_webhook['locationId'] = payload['location']['id']
    if payload.get('message'):
        message_dict = payload['message']
        # if message_dict.get('direction') == 'inbound':
        #     processed_webhook['type'] = 'InboundMessage'
        #     processed_webhook['messageType'] = str(message_dict.get('type'))
        processed_webhook['direction'] = message_dict.get('direction', 'inbound')
        processed_webhook['body'] = message_dict.get('body')
    elif payload.get('task'):
        task_dict = payload['task']
        processed_webhook['task'] = task_dict

    processed_webhook['contactId'] = payload.get('contact_id', 'no contact id')
    if payload.get('workflow'):
        workflow_dict = payload['workflow']
        processed_webhook['workflowId'] = workflow_dict.get('id', None)
        processed_webhook['workflowName'] = workflow_dict.get('name', 'noWorkflowName')
    if payload.get('noReply'):
        processed_webhook['noReply'] = payload['noReply']
    if payload.get('customData'):
        custom_data_dict = payload['customData']
        if custom_data_dict.get('type'):
            processed_webhook['type'] = custom_data_dict['type']
        else:
            processed_webhook['type'] = 'OtherCustomWebhook'
            processed_webhook['customData'] = custom_data_dict
    processed_webhook['dateAdded'] = datetime.now(timezone.utc).strftime('%Y-%m-%dT%H:%M:%S.%f')[:-3] + 'Z'
    return processed_webhook

def add_webhook_data_to_dynamodb(payload, table_name, dynamodb):
    """
    Taken from ghl_webhook_lambda.py
    """
    try:
        item_attributes = dict()
        message_events = ['InboundMessage', 'OutboundMessage']
        contact_events = ['ContactDelete', 'ContactDndUpdate']
        note_events = ['NoteCreate', 'TaskCreate']
        contact_id_key = 'contactId' if payload['type'] in note_events + message_events else 'id'
        item_attributes['SessionId'] = {'S': payload.get(contact_id_key, 'no contact id')}
        payload_type = payload['type']
        if payload_type in note_events + message_events:
            timestamp = datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M:%S')
            item_attributes['type'] = {'S': f'{payload_type}_{timestamp}'}
        else:
            item_attributes['type'] = {'S': payload.get('type', 'no event type')}
        for key, value in payload.items():
            if (key != 'type') & (key != contact_id_key):
                if type(value) == str:
                    item_attributes[key] = {'S': value}
                elif type(value) == bool:
                    item_attributes[key] = {"BOOL": value}
                elif type(value) == dict:
                    item_attributes[key] = {"S": json.dumps(value)}
                elif type(value) == list:
                    value = ''.join([f'{item}, ' for item in value])
                    item_attributes[key] = {"S": value}
                else:
                    print(f'Unable to save payload item {key} of type {type(value)}')
        try:
            location_id = payload['locationId']
            item_attributes['business'] = {"S": os.getenv(location_id, 'Not available')}
        except Exception as error:
            exc_type, exc_obj, tb = sys.exc_info()
            f = tb.tb_frame
            lineno = tb.tb_lineno
            filename = f.f_code.co_filename
            message = f"Error in line {lineno} of {filename}: {str(error)}"
            return message
        if payload_type in contact_events:
            timestamp = datetime.now(timezone.utc).strftime('%Y-%m-%dT%H:%M:%S.%f')[:-3] + 'Z'
            item_attributes['dateAdded'] = {'S': timestamp}
        dynamodb.put_item(
            TableName=table_name,
            Item=item_attributes
        )
        message = f'Data for {payload.get("type", "")} webhook saved to DynamoDB successfully.'
        lastInboundMessage = dict()
        lastInboundMessage['SessionId'] = {'S': payload.get(contact_id_key, 'no contact id')}
        lastInboundMessage['type'] = {'S': 'lastInboundMessage'}
        lastInboundMessage['messageType'] = {'S': payload.get('messageType', 'unknown')}
        if payload_type == 'InboundMessage':
            dynamodb.put_item(
                TableName=table_name,
                Item=lastInboundMessage
            )
        message += f' Last InboundMessage type saved to DynamoDB successfully.'
        return message
    except Exception as error:
        exc_type, exc_obj, tb = sys.exc_info()
        f = tb.tb_frame
        lineno = tb.tb_lineno
        filename = f.f_code.co_filename
        print("An error occurred on line", lineno, "in", filename, ":", error)
        return f"Error in line {lineno} of {filename}: {str(error)}"

def add_to_chat_history(payload):
    try:
        from langchain_community.chat_message_histories import DynamoDBChatMessageHistory
        
        contactId = payload.get('contactId', 'no contact id')

        history = DynamoDBChatMessageHistory(
            table_name="SessionTable", session_id=contactId,
            key={
                'SessionId': contactId,
                'type': 'ChatHistory'
            }
            )
        if payload['type'] == 'InboundMessage':
            history.add_user_message(payload['body'])
            message = f'Added user message to chat history for webhook type {payload["type"]}'
        elif payload['type'] == 'OutboundMessage':
            history.add_ai_message(payload['body'])
            message = f'Added AI message to chat history for webhook type {payload["type"]}'
        else:
            message = f'No chat history to save.'
        print(f'Chat history: \n{history.messages}')
    except Exception as error:
        exc_type, exc_obj, tb = sys.exc_info()
        f = tb.tb_frame
        lineno = tb.tb_lineno
        filename = f.f_code.co_filename
        message = f'An error occurred on line {lineno} in {filename}: {error}.'
    return message

def format_irish_mobile_number(phone_number):
    # Remove non-digit characters from the input string
    cleaned_number = re.sub(r'\D', '', phone_number)
    pattern = r"^(?:\+?353)?(?:08|8)\d{8}$"
    irish_number = re.search(pattern, cleaned_number)
    if irish_number:
        cleaned_number = irish_number.group(0)[-9:]
        cleaned_number = f'{cleaned_number[:2]} {cleaned_number[2:5]} {cleaned_number[5:]}'
        formatted_number = f'+353 {cleaned_number}'
        print(f"\n{phone_number} -> Formatted Irish Mobile Number: {formatted_number}\n")
        return formatted_number
    else:
        # If the input does not match the expected mobile number format, return None
        print(f"\n{phone_number} -> Invalid or non-Irish mobile number format.\n")
        return phone_number

def convert_to_pascal_case(text):
    words = text.split()
    words = [w.title() for w in words]
    return ''.join(words)