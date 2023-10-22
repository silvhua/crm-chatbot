import boto3
from boto3.dynamodb.conditions import Key

def query_dynamodb_table(table_name, value, key='SessionId', region_name="us-west-2"):
    """
    Query a Dynamodb table and print the results.
    Parameters:
        table_name (str): The name of the DynamoDB table.
        value (str): The value of the key.
        key (str): The name of the key.
        region_name (str): The name of the AWS region.

    Returns:
        dict: The results of the query. The 'Items' key contains the table record.       

    """
    dynamodb = boto3.resource('dynamodb', region_name=region_name)
    table = dynamodb.Table(table_name)
    response = table.query(
        KeyConditionExpression=Key(key).eq(value)
    )
    return response