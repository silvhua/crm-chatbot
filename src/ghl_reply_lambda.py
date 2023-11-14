import json
import sys

def lambda_handler(event, context):
    """
    This Lambda function is triggered by another function when the payload type is 'InboundMessage'.
    It prints the 'contactId' from the payload.
    """
    # Extract the payload from the event
    payload = event
    print(f'Payload: {payload}')
    contact_id = payload.get('contactId')
    print(f'Contact ID: {contact_id}')

    return {
        'statusCode': 200,
        'body': json.dumps(f'Contact ID: {contact_id}')
    }