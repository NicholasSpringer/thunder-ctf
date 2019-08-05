import os

from google.cloud import storage
import google.auth
from googleapiclient import discovery


def upload_directory_recursive(dir_path, top_dir, bucket):
    for subitem in os.listdir(dir_path):
        subitem_path = dir_path + "/" + subitem
        if os.path.isdir(subitem_path):
            upload_directory_recursive(subitem_path, top_dir, bucket)
        else:
            relative_file_path = subitem_path.replace(top_dir + '/', '', 1)
            blob = storage.Blob(relative_file_path, bucket)
            with open(subitem_path, 'rb') as f:
                blob.upload_from_file(f)


def delete_bucket(bucket_name):
    # Forcefully delete bucket to also get rid of items inside bucket
    storage_client = storage.Client()
    bucket = storage_client.lookup_bucket(bucket_name)
    if bucket:
        bucket.delete(force=True)


def service_account_email(account):
    credentials, project_id = google.auth.default()
    return f'{account}@{project_id}.iam.gserviceaccount.com'


def set_account_role(email, role):
    remove_accounts_iam([email])
    credentials, project_id = google.auth.default()
    crm_api = discovery.build('cloudresourcemanager',
                              'v1', credentials=email)
    # Get current iam policy
    policy = crm_api.projects().getIamPolicy(
        resource=project_id, body={}).execute()
    # Add binding to policy
    for binding in policy['binding']:
        if binding['role'] == role:
            binding['members'].append(f'serviceAccount:{email}')
    # Set as new policy
    crm_api.projects().setIamPolicy(resource=project_id,
                                    body={'policy': policy}).execute()


def remove_accounts_iam(emails):
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


def test_application_default_credentials():
    # Try to extract application default credentials
    try:
        credentials, project_id = google.auth.default()
    except google.auth.exceptions.DefaultCredentialsError:
        exit('Application default credentials not set. To set credentials, run:\n'
             '  gcloud auth application-default login')
    # Make sure application default project is the same as the project in thunder ctf config
    with open('core/common/config/project.txt') as f:
        set_project = f.read()
    if not set_project == project_id:
        exit(f'Application default project: {project_id} is not equal to Thunder CTF project: {set_project}. To change application default project, run:\n'
             '  gcloud config set project=[project-id]\n'
             'To change the Thunder CTF project, run:\n'
             '  python3 thunder.py set_project')
    # Build api object
    crm_api = discovery.build('cloudresourcemanager',
                              'v1', credentials=credentials)
    # Check if credentials has permissions
    response = crm_api.projects().testIamPermissions(resource=project_id, body={
        'permissions': check_permissions}).execute()
    if 'permissions' in response:
        if len(response['permissions']) == len(check_permissions):
            return True
    # If credentials don't have necessary permissions, exit
    exit(f'Application default account should have owner role on project {project_id}.\n'
         'If you are trying to use a user account, make sure GOOGLE_APPLICATION_CREDENTIALS environment variable is not set:\n'
         '  unset GOOGLE_APPLICATION_CREDENTIALS\n'
         'Set application default credentials with:\n'
         '  gcloud auth application-default login')


check_permissions = [
    'iam.roles.create', 'iam.roles.delete', 'iam.roles.get', 'iam.roles.list', 'iam.roles.undelete', 'iam.roles.update', 'iam.serviceAccounts.actAs', 'iam.serviceAccounts.create', 'iam.serviceAccounts.delete', 'iam.serviceAccounts.get', 'iam.serviceAccounts.getIamPolicy', 'iam.serviceAccounts.list', 'iam.serviceAccounts.setIamPolicy', 'iam.serviceAccounts.update', 'logging.logs.delete', 'logging.logs.list', 'resourcemanager.projects.createBillingAssignment', 'resourcemanager.projects.delete', 'resourcemanager.projects.deleteBillingAssignment', 'resourcemanager.projects.get', 'resourcemanager.projects.getIamPolicy', 'resourcemanager.projects.setIamPolicy', 'resourcemanager.projects.undelete', 'resourcemanager.projects.update', 'resourcemanager.projects.updateLiens', 'storage.buckets.create', 'storage.buckets.delete', 'storage.buckets.list', 'serviceusage.services.enable'
]


def setup_project():
    credentials, project_id = google.auth.default()
    # Build api object
    crm_api = discovery.build('cloudresourcemanager',
                              'v1', credentials=credentials)
    # Get project number
    project_num = crm_api.projects().get(
        project_id=project_id)['projectNumber']
    # Build api object
    services_api = discovery.build(
        'serviceusage', 'v1', credentials=credentials)
    # Enable apis
    apis = [
        'deploymentmanager.googleapis.com',
        'cloudresourcemanager.googleapis.com'
    ]
    request_body = {'serviceIds': apis}
    services_api.services().batchEnable(
        parent=f'projects/{project_num}', body=request_body)
    # Set deployment manager service account as owner
    set_account_role(f'{project_num}@cloudservices.gserviceaccount.com','roles/owner')
