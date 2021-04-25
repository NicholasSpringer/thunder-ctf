import random
import os
import json
import csv
import sqlalchemy
import google.auth
from pprint import pprint
from googleapiclient import discovery

from google.oauth2 import service_account
from core.framework import levels
from core.framework.cloudhelpers import (
    deployments,
    iam,
    gcstorage,
    cloudfunctions
)

LEVEL_PATH = 'defender/audit'
FUNCTION_LOCATION = 'us-central1'

def create(second_deploy=True):
    print("Level initialization started for: " + LEVEL_PATH)
    nonce = str(random.randint(100000000000, 999999999999))

    register_func_url = cloudfunctions.upload_cloud_function(
            'core/levels/defender/audit/resources/register_func',
            FUNCTION_LOCATION
            )

    config_template_args = {
        'nonce': nonce,
        'register_url': register_func_url,
        'root_password': 'psw'
        }

    template_files = [
        'core/framework/templates/cloud_function.jinja',
        'core/framework/templates/service_account.jinja',
        'core/framework/templates/iam_policy.jinja',
        'core/framework/templates/sql_db.jinja'
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
    try:
        print("Level setup started for: " + LEVEL_PATH)

        create_tables()
        user_keys = register_users()
        post_statuses()

        print(f'Level creation complete for: {LEVEL_PATH}')
        start_message = ('Helpful start message')

    except Exception as e:
        exit()

def destroy():
    deployments.delete()

def register_users():
    users = csv.DictReader(open('resources/users.csv', newline=''))

    # Hit the db api to add users to the table and generate a bunch
    # of account keys might have to wait for the service accounts
    # to register. Try every 60 seconds

def post_statuses():
    # Load statuses and post to db
    statuses = csv.DictReader(open('resources/statuses.csv', newline=''))

def create_tables():
    # Get the connection name of the db instance
    credentials, project_id = google.auth.default()
    service = discovery.build('sqladmin', 'v1beta4', credentials=credentials)
    response = service.instances().list(project=project_id).execute()
    instance_name = response['items'][0]['connectionName']

    # Download a proxy manager to authenticate connection
    subprocess.call('./auth_proxy.sh')
    proxy = subprocess.Popen(['./cloud_sql_proxy', f'-instances={instance_name}=tcp:5432'])
    time.sleep(5)

    db_config = {
        "pool_size": 5,
        "max_overflow": 2,
        "pool_recycle": 1800,  # 30 minutes
    }

    pool = sqlalchemy.create_engine(
        sqlalchemy.engine.url.URL(
            drivername="postgresql+pg8000",
            username="postgres",
            password="psw",
            host='127.0.0.1',
            port=5432,  # e.g. 5432
            database='userdata-db'
        ),
        **db_config
    )

    pool.dialect.description_encoding = None
    devs = csv.DictReader(open('resources/devs.csv', newline=''))

    with db.connect(user_db_name) as conn:
        conn.execute(
            """CREATE TABLE users (
                id       SERIAL,
                name     TEXT              NOT NULL,
                phone    TEXT              NOT NULL,
                address  TEXT              NOT NULL
            );
            CREATE TABLE devs (
                id       SERIAL,
                name     TEXT              NOT NULL,
                phone    TEXT              NOT NULL,
                address  TEXT              NOT NULL
            );"""
        )

        for dev in devs:
            query = f"""INSERT INTO devs (name, phone, address)
                        VALUES ({dev[name]}, {dev[phone]}, {dev[address]});
                    """
            conn.execute(query)

    pool.dispose()
    proxy.terminate()
    os.system(['rm', 'cloud_sql_proxy'])