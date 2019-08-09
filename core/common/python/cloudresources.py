import os
import time
import sys
import zipfile
import shutil

import httplib2
from google.cloud import storage
import google.auth
from googleapiclient import discovery


def upload_directory_recursive(top_dir_path, bucket):
    for dir_path, subdir_paths, f_names in os.walk(dir_path):
        for f in f_names:
            relative_path = dir_path + '/' + f
            abs_path = top_dir_path + '/' + relative_path
            blob = storage.Blob(relative_path, bucket)
            with open(abs_path, 'rb') as f:
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


def test_application_default_credentials(set_project=None):
    # Query user to delete environment variable
    if 'GOOGLE_APPLICATION_CREDENTIALS' in os.environ:
        if 'y' == input(f'GOOGLE_APPLICATION_CREDENTIALS is set, meaning the application default credentials will use a service account. '
                        'Unless the service account has owner access, the command will fail.'
                        'Would you like to unset GOOGLE_APPLICATION_CREDENTIALS? [y/n] ').lower()[0]:
            del os.environ['GOOGLE_APPLICATION_CREDENTIALS']
    # Try to extract application default credentials
    try:
        credentials, project_id = google.auth.default()
    except google.auth.exceptions.DefaultCredentialsError:
        exit('Application default credentials not set. To set credentials, run:\n'
             '  gcloud auth application-default login')
    # Make sure application default project is the same as the project in thunder ctf config
    if not set_project:
        with open('core/common/config/project.txt') as f:
            set_project = f.read()
    if set_project == '':
        exit('You must set the Thunder CTF project to your GCP project id:\n'
             '  python3 thunder.py set_project [project-id]')
    if not project_id:
        exit('You must the set the gcloud config account and project '
             'to your application default account and the desired project \n'
             '  gcloud config set account [email]\n'
             '  gcloud config set project [project-id]\n'
             'If you wish to reset the application default credentials, run:\n'
             '  gcloud auth application-default login')
    if not set_project == project_id:
        exit(f'Application default project id: {project_id} '
             f'is not equal to Thunder CTF project id: {set_project}. '
             'To change application default project, run:\n'
             '  gcloud config set project=[project-id]\n'
             'To change the Thunder CTF project, run:\n'
             '  python3 thunder.py set_project [project-id]')
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
         'If you are trying to use a user account, '
         'make sure GOOGLE_APPLICATION_CREDENTIALS environment variable is not set:\n'
         '  unset GOOGLE_APPLICATION_CREDENTIALS\n'
         'make sure the gcloud cli account is set the same account as application default:\n'
         '  gcloud config set account [email]\n'
         'Reset application default credentials with:\n'
         '  gcloud auth application-default login')


check_permissions = [
    'iam.roles.create', 'iam.roles.delete', 'iam.roles.get', 'iam.roles.list', 'iam.roles.undelete', 'iam.roles.update', 'iam.serviceAccounts.actAs', 'iam.serviceAccounts.create', 'iam.serviceAccounts.delete', 'iam.serviceAccounts.get', 'iam.serviceAccounts.getIamPolicy', 'iam.serviceAccounts.list', 'iam.serviceAccounts.setIamPolicy', 'iam.serviceAccounts.update', 'logging.logs.delete', 'logging.logs.list', 'resourcemanager.projects.createBillingAssignment', 'resourcemanager.projects.delete', 'resourcemanager.projects.deleteBillingAssignment', 'resourcemanager.projects.get', 'resourcemanager.projects.getIamPolicy', 'resourcemanager.projects.setIamPolicy', 'resourcemanager.projects.undelete', 'resourcemanager.projects.update', 'resourcemanager.projects.updateLiens', 'storage.buckets.create', 'storage.buckets.delete', 'storage.buckets.list', 'serviceusage.services.enable'
]


def setup_project():
    print('Setting up project.')
    credentials, project_id = google.auth.default()
    # Build api object
    crm_api = discovery.build('cloudresourcemanager',
                              'v1', credentials=credentials)
    # Get project number
    project_num = crm_api.projects().get(
        projectId=project_id).execute()['projectNumber']
    # Build api object
    services_api = discovery.build(
        'serviceusage', 'v1', credentials=credentials)
    # Enable apis
    apis = [
        'deploymentmanager.googleapis.com',
        'cloudresourcemanager.googleapis.com'
    ]
    request_body = {'serviceIds': apis}
    op_name = services_api.services().batchEnable(
        parent=f'projects/{project_num}', body=request_body).execute()['name']
    wait_for_operation(op_name, services_api)
    # Set deployment manager service account as owner
    set_account_role(
        f'{project_num}@cloudservices.gserviceaccount.com', 'roles/owner')


def wait_for_operation(op_name, services_api):
    # Wait till  operation finishes, giving updates every 5 seconds
    op_done = False
    t = 0
    start_time = time.time()
    time_string = ''
    while not op_done:
        time_string = f'[{int(t/60)}m {(t%60)//10}{t%10}s]'
        sys.stdout.write(
            f'\r{time_string} Deployment operation in progress...')
        t += 5
        while t < time.time()-start_time:
            t += 5
        time.sleep(t-(time.time()-start_time))
        response = services_api.operations().get(
            name=op_name).execute()
        if not 'done' in response:
            op_done = False
        else:
            op_done = response['done']
    sys.stdout.write(
        f'\r{time_string} Deployment operation in progress... Done\n')


def upload_cloud_function(function_path, location_id, properties={}):
    temp_func_path = function_path + '-temp'
    zip_path = os.path.dirname(temp_func_path) + '/' + 'function.zip'
    try:
        create_temp_function(function_path, temp_func_path,
                             properties=properties)
        credentials, project_id = google.auth.default()
        # Create zip
        with zipfile.ZipFile(zip_path, 'w') as z:
            for dir_path, subdir_paths, f_names in os.walk(temp_func_path):
                for f in f_names:
                    file_path = dir_path + '/' + f
                    arc_path = file_path.replace(temp_func_path+'/', '')
                    z.write(file_path, arcname=arc_path)
        # Build api object
        cf_api = discovery.build('cloudfunctions',
                                 'v1', credentials=credentials)
        parent = f'projects/{project_id}/locations/{location_id}'
        # Generate upload URL
        upload_url = cf_api.projects().locations().functions(
        ).generateUploadUrl(parent=parent).execute()['uploadUrl']
        # Make Http object
        h = httplib2.Http()
        # Upload to url
        headers = {'Content-Type': 'application/zip',
                   'x-goog-content-length-range': '0,104857600'}
        with open(zip_path, 'rb') as f:
            h.request(upload_url, method='PUT', headers=headers, body=f)
        # Return signed url for creating cloud function
        return upload_url
    finally:
        # Delete zip
        if os.path.exists(zip_path):
            os.remove(zip_path)
        # Delete temp file
        if os.path.exists(temp_func_path):
            shutil.rmtree(temp_func_path)


def create_temp_function(function_path, temp_func_path, properties={}):
    for dir_path, subdir_paths, f_names in os.walk(function_path):
        for f in f_names:
            file_path = dir_path + '/' + f
            temp_path = file_path.replace(function_path, temp_func_path)
            copy_file_replace_properties(
                file_path, temp_path, properties=properties)


def copy_file_replace_properties(origin_path, dest_path, properties={}):
    with open(origin_path) as f:
        content = f.read()
    for key in properties.keys():
        content = content.replace('//'+key+'//', properties[key])
    if not os.path.exists(os.path.dirname(dest_path)):
        os.makedirs(os.path.dirname(dest_path))
    with open(dest_path, 'w+') as f:
        f.write(content)
