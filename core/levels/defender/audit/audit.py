import random
import os
import subprocess
import time
import json
import csv
import sqlalchemy
import string
import google.auth

from googleapiclient import discovery
from sqlalchemy.sql import text
from google.oauth2 import service_account
from core.framework import levels
from google.cloud import {
    storage,
    secretmanager
}
from core.framework.cloudhelpers import (
    deployments,
    iam,
    gcstorage,
    cloudfunctions
)

LEVEL_PATH = 'defender/audit'
FUNCTION_LOCATION = 'us-central1'
DB_SECRET_ID = 'db_password'

def create(second_deploy=True):
    print("Level initialization started for: " + LEVEL_PATH)
    nonce = str(random.randint(100000000000, 999999999999))

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
    logging_key = iam.generate_service_account_key('log-viewer')
    storage_client = storage.Client()
    vm_image_bucket = storage_client.get_bucket(f'vm-image-bucket-{nonce}')
    storage_blob = storage.Blob('main.py', vm_image_bucket)
    storage_blob.upload_from_filename(f'core/levels/{LEVEL_PATH}/resources/api-engine/main.py')
    storage_blob = storage.Blob('Dockerfile', vm_image_bucket)
    storage_blob.upload_from_filename(f'core/levels/{LEVEL_PATH}/resources/api-engine/Dockerfile')
    storage_blob = storage.Blob('requirements.txt', vm_image_bucket)
    storage_blob.upload_from_filename(f'core/levels/{LEVEL_PATH}/resources/api-engine/requirements.txt')
    storage_blob = storage.Blob('cloud_sql_proxy', vm_image_bucket)
    storage_blob.upload_from_filename(f'core/levels/{LEVEL_PATH}/resources/api-engine/cloud_sql_proxy')


    print(f'Level creation complete for: {LEVEL_PATH}')
    start_message = ('Helpful start message')


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
    user = {'kind':'sql#user','name':'api-engine','project':project_id,'instance':instance_name,'password':'psw'}
    service.users().insert(project=project_id, instance=instance_name, body=user).execute()

    proxy = subprocess.Popen([f'core/levels/{LEVEL_PATH}/cloud_sql_proxy', f'-instances={connection_name}=tcp:5432'])
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
    proxy.terminate()


def delete_secret(secret_id):
    _, project_id = google.auth.default()

    # Create Secrets Manager client
    sm_client = secretmanager.SecretManagerServiceClient()

    # Build the resource name of the secret.
    name = sm_client.secret_path(project_id, secret_id)

    # Delete secret.
    sm_client.delete_secret(request={"name": name})


def destroy():
    deployments.delete()
    delete_secret(DB_SECRET_ID)