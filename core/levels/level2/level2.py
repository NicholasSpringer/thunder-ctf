import random
import os
import subprocess
import shutil

from google.cloud import storage

from ...common import deployments, secrets, keys, storage

LEVEL_NAME = 'level2'


def create():
    # Make sure level isn't already deployed
    if LEVEL_NAME in deployments.list_deployments():
        exit(f'Level {LEVEL_NAME} has already been deployed. '
             'To reload the level, first destroy the running instance.')

    print("Level initialization started for: " + LEVEL_NAME)
    # Create randomized nonce name to avoid namespace conflicts
    nonce = str(random.randint(100000000000, 999999999999))
    bucket_name = f'level2-bucket-{nonce}'

    # Create ssh key
    ssh_private_key, ssh_public_key = keys.generate_ssh_key()
    ssh_username = "clouduser"

    # Construct git repo
    repo_path = os.path.dirname(os.getcwd()) + "/temp-repository-" + nonce
    os.makedirs(repo_path + '/function')
    os.chdir(repo_path)
    # Make dummy cloud function files
    with open(repo_path+'/function/requirements.txt', 'w+') as f:
        f.write('')
    with open(repo_path+'/function/main.py', 'w+') as f:
        f.write('')
    # Add ssh key file
    with open(repo_path+'/ssh_key', 'w+') as f:
        f.write(ssh_private_key)
    os.chmod('ssh_key', 0o700)
    # Add files in first commit, then delete key in second
    subprocess.call(['git', 'init', '--q'])
    p = subprocess.Popen(['git', 'add', '*'])
    p.communicate()
    subprocess.call(['git', 'commit', '-q', '-m', 'added initial files', ])
    os.remove('ssh_key')
    p = subprocess.Popen(['git', 'add', '*'])
    p.communicate()
    subprocess.call(
        ['git', 'commit', '-q', '-m', 'Oops. Deleted accidental key upload'])
    # Reset working directory
    os.chdir(os.path.dirname(repo_path)+'/gcp-vulnerable')
    print("Level initialization finished for: " + LEVEL_NAME)

    # Insert deployment
    config_properties = {'nonce': nonce,
                         'ssh_public_key': ssh_public_key,
                         'ssh_username': ssh_username}
    labels = {'nonce': nonce}
    deployments.insert(LEVEL_NAME,
                       'config/level2.yaml',
                       template_files=[
                           'config/bucket_acl.jinja',
                           'config/instance.jinja',
                           'config/service_account.jinja',
                           'config/set_iam_policy.jinja'],
                       config_properties=config_properties, labels=labels)

    print("Level setup started for: " + LEVEL_NAME)
    # Upload repository to bucket
    storage_client = storage.Client()
    bucket = storage_client.get_bucket(bucket_name)
    storage.upload_directory_recursive(repo_path, repo_path, bucket)
    shutil.rmtree(repo_path)
    print("Level creation complete for: " + LEVEL_NAME)


def destroy():
    # Make sure level is deployed
    if not LEVEL_NAME in deployments.list_deployments():
        exit(f'Level {LEVEL_NAME} is not currently deployed')

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
