import random
import os

import google.auth
from googleapiclient import discovery
from google.cloud import storage

from core.common import levels
from core.common.cloudhelpers import deployments, iam, gcstorage, cloudfunctions

LEVEL_PATH = 'thunder/a6container'
RESOURCE_PREFIX = 'a6'
INSTANCE_ZONE = 'us-west1-b'


def create():
    print("Level initialization started for: " + LEVEL_PATH)
    # Create randomized nonce name to avoid namespace conflicts
    nonce = str(random.randint(100000000000, 999999999999))
    bucket_name = f'{RESOURCE_PREFIX}-bucket-{nonce}'
    print("Level initialization finished for: " + LEVEL_PATH)

    # Insert deployment
    config_template_args = {'nonce': nonce}
    labels = {'nonce': nonce}
    template_files = [
        'core/common/templates/bucket_acl.jinja',
        'core/common/templates/service_account.jinja',
        'core/common/templates/iam_policy.jinja',
        'core/common/templates/container_vm.jinja']
    deployments.insert(LEVEL_PATH, template_files=template_files,
                       config_template_args=config_template_args, labels=labels)

    print("Level setup started for: " + LEVEL_PATH)
    # Insert secret into bucket
    storage_client = storage.Client()
    bucket = storage_client.get_bucket(bucket_name)
    secret_blob = storage.Blob('secret.txt', bucket)
    secret = levels.make_secret(LEVEL_PATH)
    secret_blob.upload_from_string(secret)

    # Create service account key file
    sa_key = iam.generate_service_account_key(f'{RESOURCE_PREFIX}-access')
    print(f'Level creation complete for: {LEVEL_PATH}')
    start_message = (
        f'Use the compromised service account credentials stored in {RESOURCE_PREFIX}-access.json to find the secret, '
        'which is located in a file called secret.txt in a private bucket on the project.')
    levels.write_start_info(
        LEVEL_PATH, start_message, file_name=f'{RESOURCE_PREFIX}-access.json', file_content=sa_key)
    print(
        f'Instruction for the level can be accessed at thunder-ctf.cloud/levels/{LEVEL_PATH}.html')


def destroy():
    print('Level tear-down started for: ' + LEVEL_PATH)
    # Delete starting files
    levels.delete_start_files(
        LEVEL_PATH, files=[f'{RESOURCE_PREFIX}-access.json'])
    print('Level tear-down finished for: ' + LEVEL_PATH)

    # Find bucket name from deployment label
    nonce = deployments.get_labels()['nonce']
    bucket_name = f'{RESOURCE_PREFIX}-bucket-{nonce}'

    service_accounts = [
        iam.service_account_email(f'{RESOURCE_PREFIX}-access'),
        iam.service_account_email(f'{RESOURCE_PREFIX}-container-vm-sa')
    ]
    # Delete deployment
    deployments.delete(LEVEL_PATH,
                       buckets=[bucket_name],
                       service_accounts=service_accounts)
