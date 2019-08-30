import random

from google.cloud import storage

from core.framework import levels
from core.framework.cloudhelpers import deployments

LEVEL_PATH = 'thunder/a1openbucket'
RESOURCE_PREFIX = 'a1'


def create():
    # ---------Level Initialization---------
    # Create randomized bucket name to avoid namespace conflict
    nonce = str(random.randint(100000000000, 999999999999))
    bucket_name = f'{RESOURCE_PREFIX}-bucket-{nonce}'
    # --------------------------------------

    # ---------Deployment Insertion---------
    # Insert deployment
    config_template_args = {'nonce': nonce}
    template_files = ['core/framework/templates/bucket_acl.jinja']
    deployments.insert(LEVEL_PATH,
                       template_files=template_files,
                       config_template_args=config_template_args)
    # --------------------------------------

    # --------------Level Setup-------------
    print("Level setup started for: " + LEVEL_PATH)
    # Insert secret into bucket
    storage_client = storage.Client()
    bucket = storage_client.get_bucket(bucket_name)
    secret_blob = storage.Blob('secret.txt', bucket)
    secret = levels.make_secret(LEVEL_PATH)
    secret_blob.upload_from_string(secret)
    
    # Print complete message and print/save start info
    print(f'Level creation complete for: {LEVEL_PATH}\n'
          f'Instruction for the level can be accessed at thunder-ctf.cloud/levels/{LEVEL_PATH}.html')
    start_message = f'The secret for this level can be found in the Google Cloud Storage (GCS) bucket {bucket_name}'
    levels.write_start_info(LEVEL_PATH, start_message)
    # --------------------------------------


def destroy():
    # Delete starting files
    levels.delete_start_files()
    # Delete deployment
    deployments.delete()
