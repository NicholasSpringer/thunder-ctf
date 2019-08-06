import random

from google.cloud import storage

from ...common.python import deployments, secrets, levels

LEVEL_NAME = '1openbucket'


def create():
    # Create randomized bucket name to avoid namespace conflict
    nonce = str(random.randint(100000000000, 999999999999))
    bucket_name = f'{LEVEL_NAME}-bucket-{nonce}'
    # Insert deployment
    config_properties = {'nonce': nonce}
    labels = {'nonce': nonce}
    deployments.insert(LEVEL_NAME, template_files=['common/templates/bucket_acl.jinja'],
                       config_properties=config_properties, labels=labels)

    print("Level setup started for: " + LEVEL_NAME)
    # Insert secret into bucket
    storage_client = storage.Client()
    bucket = storage_client.get_bucket(bucket_name)
    secret_blob = storage.Blob('secret.txt', bucket)
    secret = secrets.make_secret(LEVEL_NAME)
    secret_blob.upload_from_string(secret)
    print(f'Level creation complete for: {LEVEL_NAME}\n'
          f'Instruction for the level can be accessed at thunder-ctf.cloud/levels/{LEVEL_NAME}')
    start_message = f'The secret for this level can be found in the Google Cloud Storage (GCS) bucket {bucket_name}'
    levels.write_start_info(LEVEL_NAME, start_message)


def destroy():
    print('Level tear-down started for: ' + LEVEL_NAME)
    # Delete starting files
    levels.delete_start_files(LEVEL_NAME)
    print('Level tear-down finished for: ' + LEVEL_NAME)
    # Find bucket name from deployment label
    nonce = deployments.get_labels(LEVEL_NAME)['nonce']
    bucket_name = f'{LEVEL_NAME}-bucket-{nonce}'
    # Delete deployment
    deployments.delete(LEVEL_NAME, buckets=[bucket_name])
