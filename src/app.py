from flask import Flask, redirect, request, jsonify
import requests
import json
from urllib.parse import urlencode

app = Flask(__name__)


# initiate.js equivalent
@app.route('/initiate')
def initiate_auth():
    with open ('../private/config.json') as config_file:
        appConfig = json.load(config_file)

    options = {
        "requestType": "code",
        "redirectUri": "http://localhost:3000/oauth/callback",
        "clientId": appConfig["clientId"],
        "scopes": [
            "conversations/message.readonly",
            "conversations/message.write",
            "contacts.readonly",
            "conversations.readonly"

        ]
    }

    redirect_url = f"{appConfig['baseUrl']}/oauth/chooselocation?response_type={options['requestType']}&redirect_uri={options['redirectUri']}&client_id={options['clientId']}&scope={' '.join(options['scopes'])}"
    return redirect(redirect_url)

# refresh.js equivalent
@app.route('/refresh')
def refresh():
    with open ('../private/config.json') as config_file:
        appConfig = json.load(config_file)
    data = {
        'client_id': appConfig["clientId"],
        'client_secret': appConfig["clientSecret"],
        'grant_type': 'refresh_token',
        'refresh_token': request.args.get('token'),
        'user_type': 'Location',
        'redirect_uri': 'http://localhost:3000/oauth/callback'
    }

    headers = {
        'Accept': 'application/json',
        'Content-Type': 'application/x-www-form-urlencoded'
    }

    response = requests.post('https://services.leadconnectorhq.com/oauth/token', data=urlencode(data), headers=headers)

    if response.status_code == 200:
        return jsonify(response.json())
    else:
        return jsonify({"error": "Failed to fetch access token."}), 500

# callback.js equivalent
@app.route('/oauth/callback')
def oauth_callback():
    with open ('../private/config.json') as config_file:
        appConfig = json.load(config_file)

    data = {
        'client_id': appConfig["clientId"],
        'client_secret': appConfig["clientSecret"],
        'grant_type': 'authorization_code',
        'code': request.args.get('code'),
        'user_type': 'Location',
        'redirect_uri': 'http://localhost:3000/oauth/callback'
    }

    headers = {
        'Accept': 'application/json',
        'Content-Type': 'application/x-www-form-urlencoded'
    }

    response = requests.post('https://services.leadconnectorhq.com/oauth/token', data=urlencode(data), headers=headers)

    if response.status_code == 200:
        return jsonify(response.json())
    else:
        return jsonify({"error": "Failed to fetch access token."}), 500

if __name__ == '__main__':
    app.run(port=3000)
