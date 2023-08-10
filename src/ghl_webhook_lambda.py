import json
import sys

def lambda_handler(event, context):
    
    try:
        # json_data = json.loads(event)
        json_data = event["body"]

        # return {
        #     'statusCode': 200,
        #     'body': json_data
        # }
        print(json_data)
        # return json_data
        return {
            "statusCode": 200,
            "body": json_data.json()
        }
    except Exception as error:
        exc_type, exc_obj, tb = sys.exc_info()
        f = tb.tb_frame
        lineno = tb.tb_lineno
        filename = f.f_code.co_filename
        print("An error occurred on line", lineno, "in", filename, ":", error)
        return {
            "statusCode": 500,
            "body": json.dumps("Error processing data: " + str(error))
        }