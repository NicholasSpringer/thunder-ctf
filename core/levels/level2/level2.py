import random
import os
import subprocess
import shutil

from google.cloud import storage

from ...common.python import deployments, secrets, keys, buckets

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
    cwd = os.getcwd()
    repo_path = os.path.dirname(cwd) + "/temp-repository-" + nonce
    os.makedirs(repo_path + '/function')
    try:
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
        os.chdir(cwd)
        print("Level initialization finished for: " + LEVEL_NAME)

        # Insert deployment
        config_properties = {'nonce': nonce,
                             'ssh_public_key': ssh_public_key,
                             'ssh_username': ssh_username}
        labels = {'nonce': nonce}
        deployments.insert(LEVEL_NAME,
                           template_files=[
                               'common/templates/bucket_acl.jinja',
                               'common/templates/instance.jinja',
                               'common/templates/service_account.jinja',
                               'common/templates/iam_policy.jinja'],
                           config_properties=config_properties, labels=labels)

        print("Level setup started for: " + LEVEL_NAME)
        # Upload repository to bucket
        storage_client = storage.Client()
        bucket = storage_client.get_bucket(bucket_name)
        buckets.upload_directory_recursive(repo_path, repo_path, bucket)
        print("Level creation complete for: " + LEVEL_NAME)
    finally:
        # If there is an error, delete the temporary repository before exiting
        shutil.rmtree(repo_path)


def destroy():
    # Make sure level is deployed
    if not LEVEL_NAME in deployments.list_deployments():
        exit(f'Level {LEVEL_NAME} is not currently deployed')

    print('Level tear-down started for: ' + LEVEL_NAME)
    # Find bucket name from deployment label
    nonce = deployments.get_labels(LEVEL_NAME)['nonce']
    bucket_name = f'bucket-{LEVEL_NAME}-{nonce}'
    # Forcefully delete bucket to also get rid of items inside bucket
    storage_client = storage.Client()
    bucket = storage_client.lookup_bucket(bucket_name)
    if bucket:
        bucket.delete(force=True)
    print('Level tear-down finished for: ' + LEVEL_NAME)
    # Delete deployment
    deployments.delete(LEVEL_NAME)
