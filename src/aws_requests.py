import boto3
from boto3.dynamodb.conditions import Key


def query_dynamodb_table(
    table_name, partition_key_value, sort_key_value='', partition_key='SessionId', sort_key=None, 
    profile='mcgill_credentials', region_name="us-west-2"
    ):
    """
    Query a Dynamodb table based on both the partition key and sort key.
    Parameters:
        table_name (str): The name of the DynamoDB table.
        partition_key_value (str): The value of the partition key.
        sort_key_value (str): The value of the sort key.
        partition_key (str): The name of the partition key.
        sort_key (str): The name of the sort key.
        region_name (str): The name of the AWS region.

    Returns:
        dict: The results of the query. The 'Items' key contains the table record.       

    Example use:
        query_dynamodb_table('SessionTable', contactId, 'ChatHistory', profile='mcgill_credentials')
    From 2023-11-12 notebook.
    """
    if profile:
        session = boto3.Session(profile_name=profile)
        dynamodb = session.resource('dynamodb', region_name=region_name)
    else:
        dynamodb = boto3.resource('dynamodb', region_name=region_name)
    table = dynamodb.Table(table_name)
    if sort_key:
        KeyConditionExpression = Key(partition_key).eq(partition_key_value) & Key(sort_key).eq(sort_key_value)
    else:
        KeyConditionExpression = Key(partition_key).eq(partition_key_value)
    print(f'KeyConditionExpression: {KeyConditionExpression}')
    response = table.query(
        KeyConditionExpression=KeyConditionExpression,
    )
    return response

