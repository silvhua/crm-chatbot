# import pytz # Not included in Lambda by default
import sys
import os
import requests
from datetime import datetime, timedelta
import json
from urllib.parse import urlencode
import boto3
import random
try:
    from dotenv import load_dotenv
    load_dotenv()
except:
    pass

def refresh_token(location='CoachMcloone', token_file_path = 'app/private'):
    """
    Refreshes the authentication token. 
    Parameters:
    - location (str): The location of the business in Pascal case, i.e. 'SamLab' or 'CoachMcloone'.
    - token_file_path (str): The path to the token file relative to the directory of the lambda function

    This function does the following:
    1. Reads the application configuration from a local file.
    2. Attempts to load the authentication tokens from a local file.
    3. If local file is not found, it retrieves the tokens from an S3 bucket.
    4. Checks if the 'SamLab' token is present in the loaded tokens. If not, it returns an error.
    5. Prepares data for the token refresh request, including client_id, client_secret, grant_type, refresh_token, user_type, and redirect_uri from the application configuration and SamLab token.
    6. Sends a POST request to the Lead Connector API to refresh the token.
    7. If the token refresh request is successful, it updates the 'SamLab' token in the loaded tokens with the response and tries to save it to a local file.
    8. If local save fails, it tries to save the tokens to the same S3 bucket.
    9. If S3 save also fails, it prints the error details.
    10. Returns the response of the token refresh request.

    Returns:
        dict: A dictionary with 'statusCode', 'body', and optionally 'response' keys. 'statusCode' is 200 if the token refresh request is successful, and 500 otherwise. 'body' contains the response of the token refresh request if it is successful, and an error message otherwise. 'response' is present only if the token refresh request fails, and contains the response of the failed request.
    """

    filename = 'auth_token_response_cicd.json'
    # filename = 'auth_token_response.json' # Original
    # config_file_name = 'config.json'
    # with open(f'{token_file_path}/{config_file_name}') as config_file:
    #     appConfig = json.load(config_file)
    appConfig = dict()
    appConfig["clientId"] = os.environ["clientId"]
    appConfig["clientSecret"] = os.environ["clientSecret"]
    
    s3 = boto3.client('s3')
    response = s3.get_object(Bucket='ownitfit-silvhua', Key=filename)
    tokens = json.loads(response['Body'].read().decode('utf-8'))
    if location in tokens:
        previous_token = tokens[location]
        print(f'Tokens retrieved from S3 for {location}.')
    else:
        return {
            'statusCode': 500,
            'body': json.dumps({"error": "SamLab token not found in token_file."})
        }

    data = {
        'client_id': appConfig["clientId"],
        'client_secret': appConfig["clientSecret"],
        'grant_type': 'refresh_token',
        'refresh_token': previous_token["refresh_token"],
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
        tokens[location] = response.json()
        # pprint(f'Tokens: {tokens["SamLab"]}')
        try:
            # Save tokens to S3
            s3 = boto3.client('s3')
            s3.put_object(
                Body=json.dumps(tokens), 
                Bucket='ownitfit-silvhua', Key=filename
                )
            print(f'Tokens saved to S3 {location}.')
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

def ghl_request(
        contactId, endpoint='createTask', text=None, payload=None, location='SamLab', 
        path_param=None, locationId=None, params_dict=None
        ):
    """
    Send a message to a contact in GoHighLevel or retrieve email history.

    Parameters:
    - contactId (str): Contact ID OR locationId if endpoint is 'getWorkflow'.
    - endpoint (str): API endpoint. Valid values are 'createTask', 'workflow', 'getWorkflow', \
    'createNote', 'send_message', 'getContacts', 'searchConversations', and 'getEmailHistory'.
    - payload (dict): Dictionary containing the payload for the request.
    - params_dict (dict): Dictionary containing additional parameters for the request.
    - location (str): Location value for retrieving the authentication token.
    - path_param (str): Additional path parameter for the request.
    - locationId: locationId for getContacts endpoint.

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
    try:
        if endpoint == 'getContact':
            endpoint_url = f'contacts/{contactId}'
            request_type = 'GET'
            payload = None
            params = None
        elif endpoint == 'createTask':
            endpoint_url = f'contacts/{contactId}/tasks'
            request_type = 'POST'
            if payload == None:
                payload = {}
                payload['title'] = ''
                if params_dict:
                    payload['title'] += f'{"Human attention needed: " if params_dict["alert_human"]==True else "Chatbot response: "}'
                    payload['body'] = params_dict['response']
                else:
                    payload['body'] = text if text else f"Test task via GHL API at {datetime.utcnow().strftime('%Y-%m-%dT%H:%M:%SZ')} Pacific time"
                payload['title'] += f'Send message to contact {contactId}'
            payload['dueDate'] = payload[3] if len(payload) > 3 else datetime.utcnow().strftime('%Y-%m-%dT%H:%M:%SZ')
            payload['completed'] = False
        elif endpoint == 'workflow':
            endpoint_url = f'contacts/{contactId}/workflow/{path_param}'
            request_type = 'POST'
            payload = {}
            payload['eventStartTime'] = (datetime.utcnow() + timedelta(minutes=random.randint(2, 10))).strftime('%Y-%m-%dT%H:%M:%S+00:00')
        elif endpoint == 'getWorkflow': ### 
            endpoint_url = r'workflows/'
            request_type = 'GET'
            params = {'locationId': contactId if contactId else locationId}
        elif endpoint == 'createNote':
            endpoint_url = f'contacts/{contactId}/notes'
            request_type = 'POST'
            if payload == None:
                payload = {}
                payload['body'] = (f"Reply to SMS (contactID {contactId}) {datetime.utcnow().strftime('%Y-%m-%dT%H:%M:%SZ')}" if text==None else text)
                payload['userId'] = contactId
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
        elif (endpoint == 'getContacts') | (endpoint == 'searchConversations'):  
            endpoint_url = f'conversations/search' if endpoint=='searchConversations' else f'contacts/' 
            request_type = 'GET'
            payload = None
            if params_dict:
                params = params_dict
            else:
                params = {
                    'locationId': locationId,
                    'query': contactId
                }
        elif endpoint == 'getConversation':
            endpoint_url = f'conversations/{contactId if contactId else path_param}'
            request_type = 'GET'
        else:
            raise ValueError("Invalid endpoint value. Valid values are 'createTask', 'createNote', 'sendMessage', and 'getEmailHistory'.")

        url = f'{url_root}{endpoint_url}'
        token_filename = 'auth_token_response_cicd.json'
        try:
            s3 = boto3.client('s3')
            response = s3.get_object(Bucket='ownitfit-silvhua', Key=token_filename)
            token = json.loads(response['Body'].read().decode('utf-8'))[location]
        except Exception as error:
            exc_type, exc_obj, tb = sys.exc_info()
            f = tb.tb_frame
            lineno = tb.tb_lineno
            filename = f.f_code.co_filename
            message = f'Error in line {lineno} of {filename}: {str(error)}'
            print(message)
            return message

        headers = {
            "Authorization": f"Bearer {token['access_token']}",
            "Version": "2021-07-28",
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
                json=payload if payload else None,
                params=params if params else None
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
            print(f'Error in line {lineno} of {filename}: {str(error)}')
            return '[Chatbot response]'
        return data
    except Exception as error:
        exc_type, exc_obj, tb = sys.exc_info()
        f = tb.tb_frame
        lineno = tb.tb_lineno
        filename = f.f_code.co_filename
        print(f'Error in line {lineno} of {filename}: {str(error)}')
        return '[Chatbot response]'

def parse_result_id(response, result_type):
    """
    Parse the GHL API response and return the `id` of the first result.
    
    Parameters:
    - response (dict): GHL API response.
    - result_type (str): Value is dependent on the GHL API endpoint:
        - 'searchConversations' endpoint --> result_type='conversations
        - 'getContacts' endpoint --> result_type='contacts'

    Returns: `id` of the first result    
    """
    first_result = response[result_type][0]
    return first_result.get('id', 'Unable to parse id')

def search_and_get_conversation(query_string, **kwargs):
    """
    [Not useful; use `ghl_request` with `endpoint='searchConversations'` instead. 
    Likely can modify this to use for sending messages.]
    Search for a conversation with a specified query string (e.g. contact name) and retrieve the conversation.

    Parameters:
        contact_name (str): The name of the contact to search for.
        **kwargs: Additional keyword arguments that can be passed to the ghl_request function.

    Returns:
        dict: The conversation response if the search is successful, otherwise the search response.
    """
    search_response = ghl_request(
        contactId=query_string, endpoint='searchConversations', **kwargs
    )
    if search_response['status_code'] != 200:
        return search_response
    else:
        conversationId = parse_result_id(search_response, 'conversations')
        conversation_response = ghl_request(
            contactId=conversationId, endpoint='getConversation', **kwargs
        )
        return conversation_response
    
def process_leads_csv(csv_filename, csv_path):
    df = load_csv(csv_filename, csv_path)
    # Update the index to start at 2 instead of zero
    df.index = df.index + 2
    print(f'Index updated to start at 2 isntead of 0.')
    return df

class Ghl:
    """
    Class for retrieving and manually updating the S3 file storing GHL authentication information.
    """

    def __init__(self, location='CoachMcloone', token_file_path = 'app/private'):
        """
        Initializes the class with the specified location and configuration file path.

        Parameters:
            location (str): The location to be set. Defaults to 'CoachMcloone'.
            token_file_path (str): The path to the token file. Defaults to 'app/private'.

        Returns:
            None
        """
        self.location = location
        self.token_file_path = token_file_path
        self.filename = 'auth_token_response_cicd.json'
        self.config_file_name = 'config.json'

    def get_token(self):
        """
        Retrieves the file storing the authentication tokens from S3.

        Returns:
            dict: A dictionary containing the retrieved authentication details for all locations.
        """

        with open(f'{self.token_file_path}/{self.config_file_name}') as config_file:
            self.appConfig = json.load(config_file)
        s3 = boto3.client('s3')
        self.response = s3.get_object(Bucket='ownitfit-silvhua', Key=self.filename)
        self.tokens = json.loads(self.response['Body'].read().decode('utf-8'))
        return self.tokens

    def update_token(self, new_tokens):
        """
        Updates S3 with the authentication information for the current location with the provided 
        dictionary.

        Parameters:
            new_tokens (dict): The dictionary of the authentication information to update to S3. 
                This should have the same structure as the dictionary returned by `get_token`.
                The location specified in the class instance should be included as one the 
                dictionary keys. e.g. if the `location` parameter is 'CoachMcloone', `new_tokens` 
                should have a key 'CoachMcloone'.

        Returns:
            dict: The response from the PUT request to S3.
        """
        
        self.tokens[self.location] = new_tokens[self.location] # Update tokens for the location
        # pprint(f'Tokens: {tokens["SamLab"]}')
        try:
            # Save tokens to S3
            s3 = boto3.client('s3')
            self.update_response = s3.put_object(
                Body=json.dumps(self.tokens), 
                Bucket='ownitfit-silvhua', Key=self.filename
                )
            if self.update_response['ResponseMetadata']['HTTPStatusCode'] == 200:
                message = f'Tokens saved to S3 {self.location}.'
            else:
                message = f'Failed to save tokens to S3 {self.location}.'
        except Exception as error:
            exc_type, exc_obj, tb = sys.exc_info()
            f = tb.tb_frame
            lineno = tb.tb_lineno
            filename = f.f_code.co_filename
            message = f"Unable to save tokens to S3. Error in line {lineno} of {filename}: {str(error)}"
        print(message)
        return self.update_response