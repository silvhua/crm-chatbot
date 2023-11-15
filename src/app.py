from flask import Flask, redirect, request, jsonify
import requests
import json
from urllib.parse import urlencode

app = Flask(__name__)


# initiate.js equivalent
@app.route('/initiate')
def initiate_auth():
    """
    Create access token for SAM lab.
    """
    with open ('private/config.json') as config_file:
        appConfig = json.load(config_file)

    options = {
        "requestType": "code",
        "redirectUri": "http://localhost:3000/oauth/callback",
        "clientId": appConfig["clientId"],
        "scopes": [
            "conversations/message.readonly",
            "conversations/message.write",
            "users.readonly",
            "conversations.readonly",
            "contacts.write",
            "contacts.readonly"
        ]
    }

    redirect_url = f"{appConfig['baseUrl']}/oauth/chooselocation?response_type={options['requestType']}&redirect_uri={options['redirectUri']}&client_id={options['clientId']}&scope={' '.join(options['scopes'])}"
    return redirect(redirect_url)

# refresh.js equivalent
import os

@app.route('/refresh')
def refresh():
    """
    Refresh access token for SAM lab.
    """
    token_file_path = 'private/auth_token_response.json'

    with open('private/config.json') as config_file:
        appConfig = json.load(config_file)

    # Read the existing tokens from the token_file
    with open(token_file_path, 'r') as token_file:
        tokens = json.load(token_file)

    if 'SamLab' in tokens:
        sam_lab_token = tokens['SamLab']
    else:
        return jsonify({"error": "SamLab token not found in token_file."}), 500

    data = {
        'client_id': appConfig["clientId"],
        'client_secret': appConfig["clientSecret"],
        'grant_type': 'refresh_token',
        'refresh_token': sam_lab_token["refresh_token"],
        'user_type': 'Location',
        'redirect_uri': 'http://localhost:3000/oauth/callback'
    }

    headers = {
        'Accept': 'application/json',
        'Content-Type': 'application/x-www-form-urlencoded'
    }

    response = requests.post('https://services.leadconnectorhq.com/oauth/token', data=urlencode(data), headers=headers)

    if response.status_code == 200:
        # Update the SamLab token in the tokens dictionary
        tokens['SamLab'] = response.json()
        # Save the updated tokens to the token_file
        with open(token_file_path, 'w') as token_file:
            json.dump(tokens, token_file)
        return jsonify(response.json())
    else:
        return jsonify({"error": f"Failed to fetch access token: {response.reason}"}), 500

# callback.js equivalent
@app.route('/oauth/callback')
def oauth_callback():
    with open ('private/config.json') as config_file:
        appConfig = json.load(config_file)
        print('Config.json loaded')

    # Read the existing tokens from the token_file
    token_file_path = 'private/auth_token_response.json'
    with open(token_file_path, 'r') as token_file:
        tokens = json.load(token_file)

    data = {
        'client_id': appConfig["clientId"],
        'client_secret': appConfig["clientSecret"],
        'grant_type': 'authorization_code',
        'code': request.args.get('code'),
        'user_type': 'Location',
        'redirect_uri': 'http://localhost:3000/oauth/callback'
    }
    print(f'Code: {data["code"]}')
    headers = {
        'Accept': 'application/json',
        'Content-Type': 'application/x-www-form-urlencoded'
    }

    response = requests.post('https://services.leadconnectorhq.com/oauth/token', data=urlencode(data), headers=headers)

    if response.status_code == 200:
        # Save the response.json() to a file
        tokens['SamLab'] = response.json()
        with open('private/auth_token_response.json', 'w') as token_file:
            json.dump(tokens, token_file)
        return jsonify(response.json())
    else:
        return jsonify({"error": "Failed to fetch access token."}), 500

if __name__ == '__main__':
    app.run(port=3000)
