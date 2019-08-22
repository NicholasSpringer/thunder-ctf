import random
import os

import google.auth
from googleapiclient import discovery
from google.cloud import storage

from ...common.python import secrets, levels
from ...common.python.cloudhelpers import deployments, iam, cloudfunctions

LEVEL_NAME = 'a5power'
RESOURCE_PREFIX = 'a5'
FUNCTION_LOCATION = 'us-central1'


def create():
    # Create randomized bucket name to avoid namespace conflict
    nonce = str(random.randint(100000000000, 999999999999))
    bucket_name = f'{RESOURCE_PREFIX}-bucket-{nonce}'

    # Set role of default cloud function account
    credentials, project_id = google.auth.default()
    iam.set_account_iam_role(
        f'{project_id}@appspot.gserviceaccount.com', 'roles/iam.roleAdmin')
    print("Level initialization finished for: " + LEVEL_NAME)

    func_upload_url = cloudfunctions.upload_cloud_function(
        f'core/levels/{LEVEL_NAME}/function', FUNCTION_LOCATION)
    # Insert deployment
    labels = {'nonce': nonce}
    config_template_args = {'nonce': nonce,
                            'func_upload_url': func_upload_url}
    template_files = [
        'core/common/templates/service_account.jinja',
        'core/common/templates/cloud_function.jinja',
        'core/common/templates/iam_policy.jinja',
        'core/common/templates/bucket_acl.jinja']
    deployments.insert(LEVEL_NAME, template_files=template_files,
                       config_template_args=config_template_args, labels=labels)

    print("Level setup started for: " + LEVEL_NAME)
    # Allow user to use default cloud function
    iam_api = discovery.build('iam', 'v1', credentials=credentials)
    policy_body = {"policy": {
        "bindings": [{
            "members": [f"serviceAccount:a5-access@{project_id}.iam.gserviceaccount.com"],
            "role": "roles/iam.serviceAccountUser"}]}}
    iam_api.projects().serviceAccounts().setIamPolicy(
        resource=f'projects/{project_id}/serviceAccounts/a5-func-{nonce}-sa@{project_id}.iam.gserviceaccount.com', body=policy_body).execute()

    # Insert secret into bucket
    storage_client = storage.Client()
    bucket = storage_client.get_bucket(bucket_name)
    secret_blob = storage.Blob('secret.txt', bucket)
    secret = secrets.make_secret(LEVEL_NAME)
    secret_blob.upload_from_string(secret)

    # Create service account key file
    sa_key = iam.generate_service_account_key(f'{RESOURCE_PREFIX}-access')
    print(f'Level creation complete for: {LEVEL_NAME}')
    start_message = (
        f'Use the compromised service account credentials stored in {RESOURCE_PREFIX}-access.json to find the secret, '
        'which is located in a file called secret.txt in a private bucket on the project.')
    levels.write_start_info(
        LEVEL_NAME, start_message, file_name=f'{RESOURCE_PREFIX}-access.json', file_content=sa_key)
    print(
        f'Instruction for the level can be accessed at thunder-ctf.cloud/levels/{LEVEL_NAME}.html')


def destroy():
    print('Level tear-down started for: ' + LEVEL_NAME)
    # Delete starting files
    levels.delete_start_files(
        LEVEL_NAME, files=[f'{RESOURCE_PREFIX}-access.json'])

    # Reset role of default cloud function account
    credentials, project_id = google.auth.default()
    iam.set_account_iam_role(
        f'{project_id}@appspot.gserviceaccount.com', 'roles/editor')

    # Reset IAM policy of default cloud function
    iam_api = discovery.build('iam', 'v1', credentials=credentials)
    policy_body = {"policy": {"bindings": []}}
    iam_api.projects().serviceAccounts().setIamPolicy(
        resource=f'projects/{project_id}/serviceAccounts/{project_id}@appspot.gserviceaccount.com', body=policy_body).execute()
    print('Level tear-down finished for: ' + LEVEL_NAME)

    # Find bucket name from deployment label
    nonce = deployments.get_labels(LEVEL_NAME)['nonce']
    bucket_name = f'{RESOURCE_PREFIX}-bucket-{nonce}'

    service_accounts = [
        iam.service_account_email(f'{RESOURCE_PREFIX}-access'),
        iam.service_account_email(f'{RESOURCE_PREFIX}-func-{nonce}-sa')
    ]
    # Delete deployment
    deployments.delete(LEVEL_NAME,
                       buckets=[bucket_name],
                       service_accounts=service_accounts)
