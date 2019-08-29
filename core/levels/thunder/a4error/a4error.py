import random
import os

import google.auth
from googleapiclient import discovery
from google.cloud import storage

from core.framework import levels
from core.framework.cloudhelpers import deployments, iam, gcstorage, cloudfunctions

LEVEL_PATH = 'thunder/a4error'
RESOURCE_PREFIX = 'a4'
FUNCTION_LOCATION = 'us-central1'
INSTANCE_ZONE = 'us-west1-b'


def create():
    print("Level initialization started for: " + LEVEL_PATH)
    # Create randomized nonce name to avoid namespace conflicts
    nonce = str(random.randint(100000000000, 999999999999))
    bucket_name = f'{RESOURCE_PREFIX}-bucket-{nonce}'

    func_template_args = {'bucket_name': bucket_name}
    # Upload function and get upload url
    func_upload_url = cloudfunctions.upload_cloud_function(
        f'core/levels/{LEVEL_PATH}/function', FUNCTION_LOCATION, template_args=func_template_args)
    print("Level initialization finished for: " + LEVEL_PATH)

    secret = levels.make_secret(LEVEL_PATH)
    # Insert deployment
    config_template_args = {'nonce': nonce,
                            'secret': secret,
                            'func_upload_url': func_upload_url}
    template_files = [
        'core/framework/templates/bucket_acl.jinja',
        'core/framework/templates/cloud_function.jinja',
        'core/framework/templates/service_account.jinja',
        'core/framework/templates/iam_policy.jinja',
        'core/framework/templates/ubuntu_vm.jinja']
    deployments.insert(LEVEL_PATH, template_files=template_files,
                       config_template_args=config_template_args)

    print("Level setup started for: " + LEVEL_PATH)
    # Insert dummy files into bucket
    gcstorage.upload_directory_recursive(
        f'core/levels/{LEVEL_PATH}/bucket', bucket_name)

    # Delete startup script that contains secret from instance metadata
    credentials, project_id = google.auth.default()
    compute_api = discovery.build(
        'compute', 'v1', credentials=credentials)
    instance_info = compute_api.instances().get(project=project_id,
                                                zone=INSTANCE_ZONE,
                                                instance=f'{RESOURCE_PREFIX}-instance').execute()
    metadata_fingerprint = instance_info['metadata']['fingerprint']
    set_metadata_body = {'fingerprint': metadata_fingerprint, 'items': []}
    compute_api.instances().setMetadata(project=project_id,
                                        zone=INSTANCE_ZONE,
                                        instance=f'{RESOURCE_PREFIX}-instance',
                                        body=set_metadata_body).execute()

    # Create service account key file
    sa_key = iam.generate_service_account_key(f'{RESOURCE_PREFIX}-access')
    print(f'Level creation complete for: {LEVEL_PATH}')
    start_message = (
        f'In this level, look for a file named "secret.txt," which is owned by "secretuser." '
        'Use the given compromised credentials to find it.')
    levels.write_start_info(
        LEVEL_PATH, start_message, file_name=f'{RESOURCE_PREFIX}-access.json', file_content=sa_key)
    print(
        f'Instruction for the level can be accessed at thunder-ctf.cloud/levels/{LEVEL_PATH}.html')


def destroy():
    # Delete starting files
    levels.delete_start_files()
    # Delete deployment
    deployments.delete()
