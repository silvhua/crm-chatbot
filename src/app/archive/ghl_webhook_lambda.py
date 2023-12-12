import json
import sys
import boto3
from datetime import datetime, timezone

def lambda_handler(event, context):
    
    try:
        if type(event["body"]) == str:
            payload = json.loads(event["body"])
        else:
            payload = event["body"]
            
        relevant_types = [
            'ContactCreate', 'ContactDelete', 'ContactDndUpdate', 
            'InboundMessage', 'OutboundMessage'
            ]
        print(f'Payload: {payload}')
        if payload['type'] in relevant_types:
            table_name = 'ghlWebhooks'
            dynamodb = boto3.client('dynamodb') # Initialize DynamoDB client
            item_attributes = dict()
            for key, value in payload.items():
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
                    print(f'Unable to save payload item {key} of type {value}')
            if payload['type'] in ['ContactDelete', 'ContactDndUpdate']:
                timestamp = datetime.now(timezone.utc).strftime('%Y-%m-%dT%H:%M:%S.%f')[:-3] + 'Z'
                item_attributes['dateAdded'] = {'S': timestamp}
            dynamodb.put_item(
                TableName=table_name,
                Item=item_attributes
            )
            message = f'Data for {payload.get("type", "")} webhook saved to DynamoDB successfully.'
        else:
            message = f'No need to save data for {payload.get("type", "")} webhook.'
        print(message)
        return {
            "statusCode": 200,
            "body": json.dumps(message)
        }
    except Exception as error:
        exc_type, exc_obj, tb = sys.exc_info()
        f = tb.tb_frame
        lineno = tb.tb_lineno
        filename = f.f_code.co_filename
        print("An error occurred on line", lineno, "in", filename, ":", error)
        return {
            "statusCode": 500,
            "body": json.dumps(f"Error in line {lineno} of {filename}: {str(error)}")
        }
