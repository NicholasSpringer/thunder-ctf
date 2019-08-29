import random
import os
import subprocess
import shutil

from google.cloud import storage, logging as glogging

from core.framework import levels
from core.framework.cloudhelpers import deployments, iam, gcstorage, ssh_keys

LEVEL_PATH = 'thunder/a2finance'
RESOURCE_PREFIX = 'a2'
LOG_NAME = 'transactions'


def create():
    print("Level initialization started for: " + LEVEL_PATH)
    # Create randomized nonce name to avoid namespace conflicts
    nonce = str(random.randint(100000000000, 999999999999))
    bucket_name = f'{RESOURCE_PREFIX}-bucket-{nonce}'

    # Create ssh key
    ssh_private_key, ssh_public_key = ssh_keys.generate_ssh_keypair()
    ssh_username = "clouduser"

    try:
        # Construct git repo
        repo_path = os.path.dirname(os.getcwd()) + "/temp-repository-" + nonce
        create_repo_files(repo_path, ssh_private_key)
        print("Level initialization finished for: " + LEVEL_PATH)

        # Insert deployment
        config_template_args = {'nonce': nonce,
                             'ssh_public_key': ssh_public_key,
                             'ssh_username': ssh_username}
        template_files = [
            'core/framework/templates/bucket_acl.jinja',
            'core/framework/templates/ubuntu_vm.jinja',
            'core/framework/templates/service_account.jinja',
            'core/framework/templates/iam_policy.jinja']
        deployments.insert(LEVEL_PATH, template_files=template_files,
                           config_template_args=config_template_args)

        print("Level setup started for: " + LEVEL_PATH)
        # Upload repository to bucket
        gcstorage.upload_directory_recursive(repo_path, bucket_name)

        # Create logs
        secret_name = create_logs()

        # Create service account key file
        sa_key = iam.generate_service_account_key(f'{RESOURCE_PREFIX}-access')
        print(f'Level creation complete for: {LEVEL_PATH}')
        start_message = (
            f'Use the compromised service account credentials stored in {RESOURCE_PREFIX}-access.json to find the credit card number of {secret_name}, '
            'which is hidden somewhere in the GCP project')
        levels.write_start_info(
            LEVEL_PATH, start_message, file_name=f'{RESOURCE_PREFIX}-access.json', file_content=sa_key)
        print(
            f'Instruction for the level can be accessed at thunder-ctf.cloud/levels/{LEVEL_PATH}.html')
    finally:
        # If there is an error, make sure to delete the temporary repository before exiting
        if os.path.exists(repo_path):
            shutil.rmtree(repo_path)


def create_repo_files(repo_path, ssh_private_key):
    cwd = os.getcwd()
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
    os.chdir(cwd)


def create_logs():
    # Load list of framework names
    with open(f'core/levels/{LEVEL_PATH}/first-names.txt') as f:
        first_names = f.read().split('\n')
    with open(f'core/levels/{LEVEL_PATH}/last-names.txt') as f:
        last_names = f.read().split('\n')
    # Randomly determine a name associated with the secret
    secret_name = (first_names[random.randint(0, 199)] + '_' +
                   last_names[random.randint(0, 299)])
    # Randomly determine an index of logging of the secret transaction
    secret_position = random.randint(0, 99)

    logger = glogging.Client().logger(LOG_NAME)
    for i in range(0, 100):
        # On secret index, log the transaction with the secret as the credit card number of the struct
        if i == secret_position:
            logger.log_struct(
                {'name': secret_name,
                 'transaction-total': f'${random.randint(1,300)}.{random.randint(0,9)}{random.randint(0,9)}',
                 'credit-card-number': levels.make_secret(LEVEL_PATH, 16)})
        else:
            # For the other entities, determine a random name
            name = (first_names[random.randint(0, 199)] + '_' +
                    last_names[random.randint(0, 299)])
            # If the name is not equal to the secret name, log the transaction with a random credit card number
            if not name == secret_name:
                logger.log_struct(
                    {'name': name,
                     'transaction-total': f'${random.randint(1,150)}.{random.randint(1,99)}',
                     'credit-card-number': str(random.randint(1000000000000000, 9999999999999999))})
    return secret_name.replace('_', ' ')


def destroy():
    print('Level tear-down started for: ' + LEVEL_PATH)
    # Delete logs
    client = glogging.Client()
    if len([entry for entry in client.list_entries(filter_=f'logName:{LOG_NAME}')]) > 0:
        logger = client.logger(LOG_NAME)
        logger.delete()
    # Delete starting files
    levels.delete_start_files()
    print('Level tear-down finished for: ' + LEVEL_PATH) 
    # Delete deployment
    deployments.delete()
