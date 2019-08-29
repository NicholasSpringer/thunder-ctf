import base64
import time

import google.auth
from googleapiclient import discovery


def service_account_email(account):
    '''Returns the service account email given the service account id. Only works for accounts created in the deployment, not for default service accounts.'''
    credentials, project_id = google.auth.default()
    return f'{account}@{project_id}.iam.gserviceaccount.com'


def set_account_iam(email, roles):
    '''Deletes the current IAM bindings for a service account and attaches the given roles to to the account.

    Parameters:
        email (str): Email of the account
        roles (list of str): Roles to attach to the account
    '''
    remove_iam_entries([email])
    time.sleep(5)
    credentials, project_id = google.auth.default()
    crm_api = discovery.build('cloudresourcemanager',
                              'v1', credentials=credentials)
    # Get current iam policy
    policy = crm_api.projects().getIamPolicy(
        resource=project_id, body={}).execute()
    # Add binding to policy
    for role in roles:
        policy['bindings'].append(
            {'role': role, 'members': [f'serviceAccount:{email}']})
    # Set as new policy
    crm_api.projects().setIamPolicy(resource=project_id,
                                    body={'policy': policy}).execute()


def remove_iam_entries(emails):
    '''Removes all IAM entries of given service account email list.

    Parameters:
        emails (list of str): List of emails to remove IAM entries for
    '''
    credentials, project_id = google.auth.default()
    crm_api = discovery.build('cloudresourcemanager',
                              'v1', credentials=credentials)
    # Get current iam policy
    policy = crm_api.projects().getIamPolicy(
        resource=project_id, body={}).execute()

    # Remove given accounts from policy
    for binding in policy['bindings']:
        binding['members'] = (
            [member for member in binding['members']
             if not member in [f'serviceAccount:{account}' for account in emails]])
    # Set as new policy
    crm_api.projects().setIamPolicy(resource=project_id,
                                    body={'policy': policy}).execute()


def generate_service_account_key(service_account_id):
    '''Returns a new a service account key for the given service account. Only works for service accounts created by the deployment, not default service accounts.

    Parameters:
        service_account_id (str): ID of service account to create key for
    
    Returns:
        str: Key file string that can be saved to a json file and used for authentication
    '''
    # Get current credentials from environment variables and build deployment API object
    credentials, project_id = google.auth.default()
    service_account_email = f'{service_account_id}@{project_id}.iam.gserviceaccount.com'
    iam_api = discovery.build('iam', 'v1', credentials=credentials)
    # Create new key
    key = iam_api.projects().serviceAccounts().keys().create(
        name=f'projects/{project_id}/serviceAccounts/{service_account_email}', body={}).execute()
    # Decode private key data to key file
    key_file_content = base64.b64decode(
        key['privateKeyData']).decode('utf-8')
    # Return json string
    return key_file_content
