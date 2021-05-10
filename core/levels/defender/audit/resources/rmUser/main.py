#removes a user from the system, requires their name and user_id

import os
import google.auth
from google.cloud import logging as glogging

def main(keys):
    logger = glogging.Client().logger("rmUser")
    if not 'name' in keys or not 'user_id' in keys:
        payload = ''
        for key in keys:
            payload = payload + key + ' '
        logger.log_struct(
                {'action': 'Remove User',
                    'error': 'Invalid request: ' + payload})
        return Response(response='Request failed. Must include name and user_id in payload. keys: ' + payload, status=400)
    
        #need to hit api endpoint for removing user here
