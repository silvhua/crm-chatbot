import json
from app.ghl_requests import *
import time
from app.Custom_Logger import *
import logging

def lambda_handler(event, context):
    """
    Refreshes the authentication token and checks the response.
    """
    refresh_token_response = dict()
    try:
        logger_level = event.get('logger_level', logging.INFO)
        logger = Custom_Logger(
            logger_name='refresh_token', level=logger_level
        )
        info_messages = []
        max_attempts = 2
        attempt_number = 0
        while attempt_number < max_attempts:
            refresh_token_response = refresh_token()  # Call the refresh_token function
            if refresh_token_response.get('statusCode', 500) // 100 == 2:
                info_messages.append(f'Token refreshed successfully.')
                logger.info(f'API response statusCode: \n{refresh_token_response.get("statusCode")}')
                if logger.logger.level <= 10:
                    logger.debug(f'API response body: \n{refresh_token_response.get("body")}')
                break
            else:
                retry_messages = []
                attempt_number += 1
                wait_interval = 10
                retry_messages.append(f'Response Status: {refresh_token_response.get("statusCode")}. \n{refresh_token_response}')
                retry_messages.append(f'Waiting {wait_interval} seconds before re-attempting GHL sendMessage request. Re-attempt {attempt_number} of {max_attempts}.')
                logger.error('\n'.join(retry_messages))
                time.sleep(wait_interval)

        logger.info('\n'.join(info_messages))
        return {
            'statusCode': 200,
            'body': json.dumps('\n'.join(info_messages))
        }
    except Exception as error:
        exc_type, exc_obj, tb = sys.exc_info()
        f = tb.tb_frame
        lineno = tb.tb_lineno
        filename = f.f_code.co_filename
        message = f'[ERROR] An error occurred on line {lineno} in {filename}: {error}.\nAPI response: \n{refresh_token_response}'
        logger = logging.getLogger()
        logger.error(message)
        return {
            'statusCode': 500,
            'body': json.dumps(message)
        }

