import random
import os
import subprocess

from google.cloud import storage

from ...common import deployments, secrets, keys

LEVEL_NAME = 'level2'


def create():
    print("Level initialization started for: " + LEVEL_NAME)
    # Make sure level isn't already deployed
    if LEVEL_NAME in deployments.list_deployments():
        raise Exception(f'Level {LEVEL_NAME} has already been deployed. '
                        'To reload the level, first destroy the running instance.')
                        
    # Create randomized nonce name to avoid namespace conflicts
    nonce = str(random.randint(100000000000, 999999999999))
    bucket_name = f'bucket-{LEVEL_NAME}-{nonce}'

    # Create ssh key
    ssh_private_key, ssh_public_key = keys.generate_ssh_key()

    # Construct git repo
    repo_path = os.path.dirname(os.getcwd()) + "/temp-repository" + nonce
    os.makedirs(repo_path + '/function')
    os.chdir(repo_path)
    # Make dummy cloud function files
    with open(repo_path+'/function/requirements.txt', 'w+') as f:
        f.write()
    with open(repo_path+'/function/main.py', 'w+') as f:
        f.write()
    # Add ssh key file
    with open(repo_path+'/ssh_key', 'w+') as f:
        f.write(ssh_private_key)
    os.chmod('ssh_key', 0o700)
    # Add files in first commit, then delete key in second
    subprocess.call(['git', 'add', '*'])
    subprocess.call(['git', 'commit', '-m', 'added initial files'])
    os.remove('ssh_key')
    subprocess.call(['git', 'add', '*'])
    subprocess.call(
        ['git', 'commit', '-m', 'Oops. Deleted accidental key upload'])
    print("Level initialization finished for: " + LEVEL_NAME)

    # Insert deployment
    config_properties = {'nonce': nonce,
                         'ssh_public_key': ssh_public_key}
    labels = {'nonce': nonce}
    deployments.insert(LEVEL_NAME, 'config/level1.yaml', template_files=['config/bucket.jinja'],
                       config_properties=config_properties, labels=labels)

    print("Level setup started for: " + LEVEL_NAME)
    # Insert secret into bucket
    storage_client = storage.Client()
    bucket = storage_client.get_bucket(bucket_name)
    secret_blob = storage.Blob('secret.txt', bucket)
    secret = secrets.make_secret(LEVEL_NAME)
    secret_blob.upload_from_string(secret)
    print("Level creation complete for: " + LEVEL_NAME)


def destroy():
    # Make sure level is deployed
    if not LEVEL_NAME in deployments.list_deployments():
        raise Exception(f'Level {LEVEL_NAME} is not currently deployed')
    print('Level tear-down started for: ' + LEVEL_NAME)
    # Find bucket name from deployment label
    nonce = deployments.get_labels(LEVEL_NAME)['nonce']
    bucket_name = f'bucket-{LEVEL_NAME}-{nonce}'
    # Delete secret from bucket
    storage_client = storage.Client()
    bucket = storage_client.get_bucket(bucket_name)
    storage.Blob('secret.txt', bucket).delete()
    print('Level tear-down finished for: ' + LEVEL_NAME)
    # Delete deployment
    deployments.delete(LEVEL_NAME)
