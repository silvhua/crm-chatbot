import json
import requests
import urllib.parse

def lambda_handler(event, context):
    token_file_path = '../private/auth_token_response.json'

    with open('../private/config.json') as config_file:
        appConfig = json.load(config_file)

    with open(token_file_path, 'r') as token_file:
        tokens = json.load(token_file)

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

    response = requests.post('https://services.leadconnectorhq.com/oauth/token', data=urllib.parse.urlencode(data), headers=headers)

    if response.status_code == 200:
        tokens['SamLab'] = response.json()
        with open(token_file_path, 'w') as token_file:
            json.dump(tokens, token_file)
        return {
            'statusCode': 200,
            'body': json.dumps(response.json())
        }
    else:
        return {
            'statusCode': 500,
            'body': json.dumps({"error": "Failed to fetch access token."})
        }