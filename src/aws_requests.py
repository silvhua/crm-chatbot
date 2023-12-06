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

def get_dynamodb_table(
    table_name, sort_key_value='ChatHistory', partition_key_value=None, partition_key='SessionId', sort_key='type', 
    profile='mcgill_credentials', region_name="us-west-2", limit=100, last_evaluated_key=None, use_scan=False
):
    """
    Query or scan a DynamoDB table based on both the partition key and sort key, or only the sort key.
    
    Parameters:
        table_name (str): The name of the DynamoDB table.
        partition_key_value (str): The value of the partition key.
        sort_key_value (str): The value of the sort key.
        partition_key (str): The name of the partition key.
        sort_key (str): The name of the sort key.
        profile (str): The AWS credentials profile.
        region_name (str): The name of the AWS region.
        limit (int): The maximum number of items to be returned.
        last_evaluated_key (dict): The key to start reading results from.
        use_scan (bool): Whether to perform a scan instead of a query.

    Returns:
        dict: The results of the query or scan. The 'Items' key contains the table records.

    Example use:
        result = get_dynamodb_table('SessionTable', 'YourPartitionKeyValue', limit=10)
        From 2023-12-05 Codeium chat.
    """

    if profile:
        session = boto3.Session(profile_name=profile)
        dynamodb = session.resource('dynamodb', region_name=region_name)
    else:
        dynamodb = boto3.resource('dynamodb', region_name=region_name)

    table = dynamodb.Table(table_name)

    if use_scan and sort_key:
        print('Using scan...')
        filter_expression = Key(sort_key).eq(sort_key_value)
        params = {
            'FilterExpression': filter_expression
        }
        if last_evaluated_key:
            params['ExclusiveStartKey'] = last_evaluated_key

        if limit:
            params['Limit'] = limit

        response = table.scan(**params)
    else:
        print('Using query...')
        key_condition_expression = Key(partition_key).eq(partition_key_value)
        if sort_key:
            key_condition_expression &= Key(sort_key).eq(sort_key_value)
        params = {
            'KeyConditionExpression': key_condition_expression,
            'Limit': limit
        }
        if last_evaluated_key:
            params['ExclusiveStartKey'] = last_evaluated_key

        response = table.query(**params)

    return response

def dynamodb_response_to_df(response):
    # Extract the 'Items' list from the DynamoDB response
    items = response.get('Items', [])
    
    # Create an empty dictionary
    df_dict = {}
    
    # Iterate over the items and add them to the dictionary
    for item in items:
        session_id = item.get('SessionId', {})
        message_history = item.get('History', {})
        data = [
            {
                'type': message['data']['type'],
                'content': message['data']['content']
            } for message in message_history
            ]
        
        # Create a DataFrame for the current item
        df = pd.DataFrame(data)
        
        # Add the DataFrame to the dictionary with the session_id as the key
        df_dict[session_id] = df
    
    return df_dict