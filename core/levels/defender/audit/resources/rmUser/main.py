#hypothetically removes a user from the system, requires their name and user_id
#the purpose of this function is purely to generate realistic logs

import requests
import google.auth
from google.cloud import logging as glogging
from googleapiclient import discovery
from flask import Response

def main(request):
    logger = glogging.Client().logger("rmUser")
    if not 'name' in request.form or not 'user_id' in request.form or not 'authentication' in request.form:
        payload = ''
        for key in request.form:
            payload = payload + key + ' '
        target = str(request.form.get('name'))
        auth = str(request.form.get('authentication'))
        logger.log_struct(
                {'action': 'Remove User',
                    'error': 'Invalid request: ' + payload,
                    'target': target,
                    'auth': auth,
                    'logger': 'rmUser'})
        return Response(response = 'Request failed. Must include name, user_id, and id token for authentication in payload. keys: ' + payload + '\n', status = 400)

        #need to hit api endpoint for removing user here

    credentials, project_id = google.auth.default()
    service = discovery.build('compute', 'v1', credentials=credentials)
    response = service.instances().list(project=project_id, zone='us-west1-b').execute()

    for instance in response['items']:
        if instance['name'] == 'api-engine':
            hostname = instance['networkInterfaces'][0]['accessConfigs'][0]['natIP']
            break

    url = "http://" + hostname + '/delete'

    return requests.post(url)
