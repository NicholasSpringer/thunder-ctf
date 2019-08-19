import base64
import time

import google.auth
from googleapiclient import discovery

def service_account_email(account):
    credentials, project_id = google.auth.default()
    return f'{account}@{project_id}.iam.gserviceaccount.com'


def set_account_iam_role(email, role):
    remove_iam_entries([email])
    time.sleep(5)
    credentials, project_id = google.auth.default()
    crm_api = discovery.build('cloudresourcemanager',
                              'v1', credentials=credentials)
    # Get current iam policy
    policy = crm_api.projects().getIamPolicy(
        resource=project_id, body={}).execute()
    # Add binding to policy
    for binding in policy['bindings']:
        if binding['role'] == role:
            binding['members'].append(f'serviceAccount:{email}')
    # Set as new policy
    crm_api.projects().setIamPolicy(resource=project_id,
                                    body={'policy': policy}).execute()

def remove_iam_entries(emails):
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