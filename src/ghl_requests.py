import requests
from datetime import datetime
import json
import sys

def ghl_request(contactId, endpoint='createTask', text=None, payload=None, location='SamLab'):
    """
    Send a message to a contact in GoHighLevel or retrieve email history.

    Parameters:
    - contactId (str): Contact ID.
    - endpoint (str): API endpoint. Valid values are 'createTask', 'createNote', 'send_message', and 'getEmailHistory'.
    - payload (dict): Dictionary containing the payload for the request.
    - params_dict (dict): Dictionary containing additional parameters for the request.
    - location (str): Location value for retrieving the authentication token.

    Example payload for sendMessage endpoint:
        
            payload = {
                "type": "Email",
                "message": f"Hi, me. This is a test message from the GHL API using Python at {timestamp} Pacific time",
                "subject": "Testing GHL API with Python threadId",
                "emailFrom": "Brian Quinlan <brian@ownitfit.com.au>",
                "threadId": 'Y0ecBIIPiHa7bpZr616G'
            }

    Returns:
    - response_dict (dict): Dictionary containing the response from the API.
    """
    url_root = 'https://services.leadconnectorhq.com/'
    if payload:
        print(f'input payload: {payload}')

    if endpoint == 'createNote':
        endpoint_url = f'contacts/{contactId}/notes'
        request_type = 'POST'
        if payload == None:
            payload = {}
            payload['body'] = (f"Send message to contact {contactId} {datetime.utcnow().strftime('%Y-%m-%dT%H:%M:%SZ')}" if text==None else text)
            payload['userId'] = contactId
    elif endpoint == 'createTask':
        endpoint_url = f'contacts/{contactId}/tasks'
        request_type = 'POST'
        if payload == None:
            payload = {}
            payload['title'] = f'Send message to contact {contactId}' if text==None else text
        payload['dueDate'] = payload.get('dueDate', datetime.utcnow().strftime('%Y-%m-%dT%H:%M:%SZ'))
        payload['completed'] = False
    elif endpoint == 'sendMessage':
        endpoint_url = f'conversations/messages'
        request_type = 'POST'
        payload["contactId"] = contactId
        if payload['type'] == 'Email':
            payload['html'] = payload['message']
    elif endpoint == 'getEmailHistory':
        endpoint_url = f'conversations/search?contactId={contactId}'
        request_type = 'GET'
        payload = None
    else:
        raise ValueError("Invalid endpoint value. Valid values are 'createTask', 'createNote', 'sendMessage', and 'getEmailHistory'.")

    url = f'{url_root}{endpoint_url}'
    with open('../private/auth_token_response.json') as token_file:
        token = json.load(token_file)[location]

    headers = {
        "Authorization": f"Bearer {token['access_token']}",
        "Version": "2021-04-15",
        "Content-Type": "application/json",
        "Accept": "application/json"
    }

    if request_type == 'POST':
        response = requests.post(
            url, headers=headers, 
            json=payload if payload else None
        )
    elif request_type == 'GET':
        response = requests.get(
            url, headers=headers, 
            json=payload if payload else None
        )
    else:
        raise ValueError("Invalid request type. Valid values are 'POST' and 'GET'.")

    print(f'Status code {response.status_code}: {response.reason}')
    data = response.json()
    try:
        if endpoint == 'getEmailHistory':
            email_timestamp = data['conversations'][0]['dateUpdated']/1000
            utc_time = datetime.utcfromtimestamp(email_timestamp)
            pacific_time = utc_time.replace(tzinfo=pytz.utc).astimezone(pytz.timezone('US/Pacific'))
            email_timestamp_str = pacific_time.strftime('%Y-%m-%d %H:%M:%S')

            print(f'Last email sent: {email_timestamp_str} Pacific time')
            data['emailTimestamp_pacific'] = email_timestamp_str
    except Exception as error:
        exc_type, exc_obj, tb = sys.exc_info()
        f = tb.tb_frame
        lineno = tb.tb_lineno
        filename = f.f_code.co_filename
        print("An error occurred on line", lineno, "in", filename, ":", error)
    return data