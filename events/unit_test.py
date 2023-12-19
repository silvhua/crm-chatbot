import json
import sys
sys.path.append('../')
sys.path.append('../src')
sys.path.append('../src/app')
from src import ghl_chat_history_lambda
import pytest
from app import data_functions
from datetime import datetime, timezone
import os

def load_json(filename, filepath):
    """
    Load a JSON file using specified file path copied from windows file explorer.
    Back slashes in file path will be converted to forward slashes.

    Arguments:
    - filepath (raw string): Use the format r'<path>'.
    - filename (string).
    """
    filename = f'{filepath}/'.replace('\\','/')+filename
    with open(filename) as file:
        return json.load(file)

@pytest.fixture()
def apigw_event():
    job = os.environ.get('JOB_NAME')
    if job == 'test':
        test = 'ContactCreateTest.json'
    else:
        test = 'InboundMessageTest.json'
    result =  load_json(test, '.')
    timestamp = datetime.now(timezone.utc).strftime('%Y-%m-%dT%H:%M:%S.%f')[:-3] + 'Z'
    result['dateAdded'] = timestamp
    return result

def test_lambda_handler(apigw_event):

    ret = ghl_chat_history_lambda.lambda_handler(apigw_event, "")
    data = json.loads(ret["body"])

    assert ret["statusCode"] == 200, data
