import requests
from datetime import datetime
import json

def send_message(contactId, message_dict, location='SamLab'):
    """
    Send a message to a contact in GoHighLevel.
    
    Parameters:
    - contactId (str): Contact ID.
    - message_dict (dict): Dictionary containing message parameters. Dictionary keys should be:
        - type (str): 'Email' or 'SMS'.
        - message (str): Message body.
        - subject (str): Email subject line.
        - emailFrom (str): Email sender as shown in the email.

        Here is an example message_dict:
        
            message_dict = {
                "type": "Email",
                "message": f"Hi, me. This is a test message from the GHL API using Python at {timestamp} Pacific time",
                "subject": "Testing GHL API with Python threadId",
                "emailFrom": "Brian Quinlan <brian@ownitfit.com.au>",
                "threadId": 'Y0ecBIIPiHa7bpZr616G'
            }
    Returns:
    - response_dict (dict): Dictionary containing the response from the API.
    """
    url = "https://services.leadconnectorhq.com/conversations/messages"
    with open('../private/auth_token_response.json') as token_file:
        token = json.load(token_file)[location]
    type = message_dict['type']
    message = message_dict['message']
    subject = message_dict['subject']
    threadId = message_dict.get('threadId', None)
    print(f'Sending {type} messages with these parameters:')
    print(message_dict)

    payload = {
        "type": type,
        "contactId": contactId
    }
    if type == 'Email':
        emailFrom = message_dict['emailFrom']
        payload['emailFrom'] = emailFrom
        payload['html'] = message
        payload["subject"] = subject
    elif type == 'SMS':
        payload['message'] = message
        
    
    if threadId:
        payload['threadId'] = threadId
    
    headers = {
        "Authorization": f"Bearer {token['access_token']}",
        "Version": "2021-04-15",
        "Content-Type": "application/json",
        "Accept": "application/json"
    }
    response = requests.post(url, json=payload, headers=headers)
    print(f'Status code {response.status_code}: {response.reason}')

    return response.json()

def get_email_history(contactId, message_dict, location='SamLab'):
    """
    """
    url = f"https://services.leadconnectorhq.com/conversations/search?contactId={contactId}"
    with open('../private/auth_token_response.json') as token_file:
        token = json.load(token_file)[location]
    
    headers = {
        "Authorization": f"Bearer {token['access_token']}",
        "Version": "2021-04-15",
        "Accept": "application/json"
    }
    response = requests.get(url, headers=headers)
    print(f'Status code {response.status_code}: {response.reason}')

    return response.json()

iteration = 1.5
timestamp = datetime.strftime(datetime.now(), '%Y-%m-%d %H:%M:%S')
message_dict = {
    "type": "Email",
    "message": f"Hi, me. This is a test message from the GHL API using Python at {timestamp} Pacific time",
    "subject": "Testing GHL API with Python threadId",
    "emailFrom": "Brian Quinlan <brian@ownitfit.com.au>",
}
# response_dict[iteration] = get_email_history(contacts['me'], message_dict)
response_dict[iteration] = send_message(contacts['me_mcloone'], message_dict, location='CoachMcloone')
response_dict[iteration]