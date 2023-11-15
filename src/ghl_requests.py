import requests
from datetime import datetime
import json
import sys
from urllib.parse import urlencode
import boto3

def refresh_token():
    token_file_path = 'private'
    filename = 'auth_token_response.json'

    with open(f'{token_file_path}/config.json') as config_file:
        appConfig = json.load(config_file)
    try:
        with open(f'{token_file_path}/{filename}', 'r') as token_file:
            tokens = json.load(token_file)
    except:
        # Load JSON from S3
        s3 = boto3.client('s3')
        response = s3.get_object(Bucket='ownitfit-silvhua', Key=filename)
        tokens = json.loads(response['Body'].read().decode('utf-8'))
    if 'SamLab' in tokens:
        sam_lab_token = tokens['SamLab']
    else:
        return {
            'statusCode': 500,
            'body': json.dumps({"error": "SamLab token not found in token_file."})
        }

    data = {
        'client_id': appConfig["clientId"],
        'client_secret': appConfig["clientSecret"],
        'grant_type': 'refresh_token',
        'refresh_token': sam_lab_token["refresh_token"],
        'user_type': 'Location',
        # 'redirect_uri': 'https://6r8pb7q836.execute-api.us-west-2.amazonaws.com/oauth/callback',
        'redirect_uri': 'http://localhost:3000/oauth/callback'
    }

    headers = {
        'Accept': 'application/json',
        'Content-Type': 'application/x-www-form-urlencoded'
    }

    response = requests.post('https://services.leadconnectorhq.com/oauth/token', data=urlencode(data), headers=headers)

    if response.status_code == 200:
        tokens['SamLab'] = response.json()
        try:
            with open(f'{token_file_path}/{filename}', 'w') as token_file:
                json.dump(tokens, token_file)
        except:
            try:
                # Save tokens to S3
                s3 = boto3.client('s3')
                s3.put_object(
                    Body=json.dumps(tokens), 
                    Bucket='ownitfit-silvhua', Key=filename
                    )
            except Exception as error:
                exc_type, exc_obj, tb = sys.exc_info()
                f = tb.tb_frame
                lineno = tb.tb_lineno
                filename = f.f_code.co_filename
                print(f"Unable to save tokens to S3. Error in line {lineno} of {filename}: {str(error)}")
        return {
            'statusCode': 200,
            'body': json.dumps(response.json())
        }
    else:
        return {
            'statusCode': 500,
            'body': json.dumps({"error": f"Failed to fetch access token: {response.reason}",}),
            'response': json.dumps(response.json())
        }

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
            payload['body'] = (f"Reply to SMS (contactID {contactId}) {datetime.utcnow().strftime('%Y-%m-%dT%H:%M:%SZ')}" if text==None else text)
            payload['userId'] = contactId
    elif endpoint == 'createTask':
        endpoint_url = f'contacts/{contactId}/tasks'
        request_type = 'POST'
        if payload == None:
            payload = {}
            payload['title'] = f'Send message to contact {contactId}'
            payload['body'] = text if text else f"Test task via GHL API at {datetime.utcnow().strftime('%Y-%m-%dT%H:%M:%SZ')} Pacific time"
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
    data['status_code'] = response.status_code
    data['response_reason'] = response.reason
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