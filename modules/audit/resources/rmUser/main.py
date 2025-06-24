import os
import requests
import google.auth
from google.cloud import logging as glogging
from googleapiclient import discovery
from flask import Response

def main(request):
    logger = glogging.Client().logger("rmUser")

    # Validate request
    if not all(k in request.form for k in ['name', 'user_id', 'authentication']):
        payload = ' '.join(request.form.keys())
        logger.log_struct({
            'action': 'Remove User',
            'error': 'Invalid request: ' + payload,
            'target': request.form.get('name', 'MISSING'),
            'auth': request.form.get('authentication', 'MISSING'),
            'logger': 'rmUser'
        })
        logger.flush()
        return Response(
            response='Missing required fields. Provide name, user_id, and authentication.\n',
            status=400
        )

    # Extract and log request info
    name = request.form['name']
    user_id = request.form['user_id']
    auth_data = request.form['authentication']

    credentials, project_id = google.auth.default()
    zone = os.environ.get('ZONE', 'us-central1-a')  # fallback zone
    compute = discovery.build('compute', 'v1', credentials=credentials)

    # Find VM external IP
    try:
        response = compute.instances().list(project=project_id, zone=zone).execute()
        hostname = None
        for instance in response.get('items', []):
            if instance['name'] == 'api-engine':
                hostname = instance['networkInterfaces'][0]['accessConfigs'][0]['natIP']
                break
        if not hostname:
            raise Exception("Instance 'api-engine' not found.")
    except Exception as e:
        logger.log_struct({
            'action': 'Remove User',
            'error': f'VM lookup failed: {str(e)}',
            'auth': auth_data,
            'logger': 'rmUser'
        })
        logger.flush()
        return Response("Internal error locating VM.", status=500)

    url = f"http://{hostname}/delete"

    # Send simulated delete request
    try:
        resp = requests.post(url, data={
            'name': name,
            'user_id': user_id
        }, timeout=5)
    except Exception as e:
        logger.log_struct({
            'action': 'Remove User',
            'error': f"Request to VM failed: {str(e)}",
            'auth': auth_data,
            'logger': 'rmUser'
        })
        logger.flush()
        return Response("Request to backend failed", status=500)

    # ✅ Log success with authentication key (leak point)
    logger.log_struct({
        'action': 'Remove User',
        'status': 'Request sent to backend',
        'target': name,
        'auth': auth_data,
        'logger': 'rmUser'
    })
    logger.flush()

    return Response("User removed", status=200)
