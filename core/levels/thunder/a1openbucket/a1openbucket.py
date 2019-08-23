import random

from google.cloud import storage

from core.common import levels
from core.common.cloudhelpers import deployments

LEVEL_PATH = 'thunder/a1openbucket'
RESOURCE_PREFIX = 'a1'

def create():
    # Create randomized bucket name to avoid namespace conflict
    nonce = str(random.randint(100000000000, 999999999999))
    bucket_name = f'{RESOURCE_PREFIX}-bucket-{nonce}'
    # Insert deployment
    config_template_args = {'nonce': nonce}
    labels = {'nonce': nonce}
    deployments.insert(LEVEL_PATH, template_files=['core/common/templates/bucket_acl.jinja'],
                       config_template_args=config_template_args, labels=labels)

    print("Level setup started for: " + LEVEL_PATH)
    # Insert secret into bucket
    storage_client = storage.Client()
    bucket = storage_client.get_bucket(bucket_name)
    secret_blob = storage.Blob('secret.txt', bucket)
    secret = levels.make_secret(LEVEL_PATH)
    secret_blob.upload_from_string(secret)
    print(f'Level creation complete for: {LEVEL_PATH}\n'
          f'Instruction for the level can be accessed at thunder-ctf.cloud/levels/{LEVEL_PATH}.html')
    start_message = f'The secret for this level can be found in the Google Cloud Storage (GCS) bucket {bucket_name}'
    levels.write_start_info(LEVEL_PATH, start_message)


def destroy():
    print('Level tear-down started for: ' + LEVEL_PATH)
    # Delete starting files
    levels.delete_start_files(LEVEL_PATH)
    print('Level tear-down finished for: ' + LEVEL_PATH)
    # Find bucket name from deployment label
    nonce = deployments.get_labels()['nonce']
    bucket_name = f'{RESOURCE_PREFIX}-bucket-{nonce}'
    # Delete deployment
    deployments.delete(LEVEL_PATH, buckets=[bucket_name])
