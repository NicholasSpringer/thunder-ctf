import os
import time
import sys

import google.auth
from googleapiclient import discovery

from .config import cfg
from .cloudhelpers import iam


# Permissions to check if account has owner access
check_permissions = [
    'iam.roles.create', 'iam.roles.delete', 'iam.roles.get', 'iam.roles.list', 'iam.roles.undelete', 'iam.roles.update', 'iam.serviceAccounts.actAs', 'iam.serviceAccounts.create', 'iam.serviceAccounts.delete', 'iam.serviceAccounts.get', 'iam.serviceAccounts.getIamPolicy', 'iam.serviceAccounts.list', 'iam.serviceAccounts.setIamPolicy', 'iam.serviceAccounts.update', 'logging.logs.delete', 'logging.logs.list', 'resourcemanager.projects.createBillingAssignment', 'resourcemanager.projects.delete', 'resourcemanager.projects.deleteBillingAssignment', 'resourcemanager.projects.get', 'resourcemanager.projects.getIamPolicy', 'resourcemanager.projects.setIamPolicy', 'resourcemanager.projects.undelete', 'resourcemanager.projects.update', 'resourcemanager.projects.updateLiens', 'storage.buckets.create', 'storage.buckets.delete', 'storage.buckets.list', 'serviceusage.services.enable'
]


def test_application_default_credentials(tctf_project=None):
    '''Tests to make sure the Thunder CTF config project and gcloud CLI project are the same, and that the application default credentials give owner access to the project.

    Parameters:
        tctf_project (str, optional): Overrides Thunder CTF config project id. If not supplied, the project will be read from "core/framework/config/project.txt"
    '''
    # Query user to delete environment variable
    if 'GOOGLE_APPLICATION_CREDENTIALS' in os.environ:
        if 'y' == input(f'GOOGLE_APPLICATION_CREDENTIALS is set, meaning the application default credentials will use a service account. '
                        'Unless the service account has owner access, the command will fail.'
                        'Would you like to unset GOOGLE_APPLICATION_CREDENTIALS? [y/n] ').lower().strip()[0]:
            del os.environ['GOOGLE_APPLICATION_CREDENTIALS']
    # Try to extract application default credentials
    try:
        credentials, project_id = google.auth.default()
    except google.auth.exceptions.DefaultCredentialsError:
        exit('Application default credentials not set. To set credentials, run:\n'
             '  gcloud auth application-default login')

    # Make sure application default project is the same as the project in thunder ctf config
    if not tctf_project:
        tctf_project = cfg.get_project()
    if not project_id:
        exit('You must the set the gcloud cli project: \n'
             '  gcloud config set project [project-id]')
    if not tctf_project == project_id:
        exit('gcloud CLI project ID is not equal to Thunder CTF config project ID'
             f'gcloud CLI project id: {project_id if not project_id=="" else "None"}\n'
             f'Thunder CTF project id: {tctf_project if not tctf_project=="" else "None"}.\n'
             'To change gcloud cli project, run:\n'
             '  gcloud config set project=[project-id]\n'
             'To change the Thunder CTF project, run:\n'
             '  python3 thunder.py activate_project [project-id]')
    # Build api object
    crm_api = discovery.build('cloudresourcemanager',
                              'v1', credentials=credentials)
    # Check if credentials have permissions
    response = crm_api.projects().testIamPermissions(resource=project_id, body={
        'permissions': check_permissions}).execute()
    if 'permissions' in response:
        if len(response['permissions']) == len(check_permissions):
            return True
    # If credentials don't have necessary permissions, exit
    exit(f'Application default account should have owner role on project {project_id}.\n'
         'make sure you spelled the project ID correctly and the account')


def setup_project():
    '''Enables necessary Google Cloud APIs, 
        gives the deployment manager owner permission on the gcloud cli config project, 
        and adds the default-allow-http firewall rule.'''
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
        'cloudapis.googleapis.com',
        'cloudfunctions.googleapis.com',
        'cloudbuild.googleapis.com',
        'cloudresourcemanager.googleapis.com',
        'compute.googleapis.com',
        'datastore.googleapis.com',
        'iam.googleapis.com',
        'iamcredentials.googleapis.com',
        'logging.googleapis.com',
        'deploymentmanager.googleapis.com',
        'storage-api.googleapis.com',
        'storage-component.googleapis.com',
        'appengine.googleapis.com',
        'vision.googleapis.com'
    ]
    request_body = {'serviceIds': apis}
    op_name = services_api.services().batchEnable(
        parent=f'projects/{project_num}', body=request_body).execute()['name']
    _wait_for_api_op(op_name, services_api)
    print('Configuring DM role...')
    # Set deployment manager service account as owner
    iam.set_account_iam(
        f'{project_num}@cloudservices.gserviceaccount.com', ['roles/owner'])
    print('Configuring firewall rules...')
    # Add the default-allow-http firewall rule
    compute_api = discovery.build('compute', 'v1', credentials=credentials)
    firewall_list = compute_api.firewalls().list(project=project_id).execute()
    if not 'default-allow-http' in [firewall['name'] for firewall in firewall_list['items']]:
        firewall_body = {'allowed':
                         [{'IPProtocol': 'tcp',
                           'ports': ['80']}],
                         'direction': 'INGRESS',
                         'disabled': False,
                         'logConfig': {
                             'enable': False},
                         'name': 'default-allow-http',
                         'sourceRanges': ['0.0.0.0/0'],
                         'targetTags': ['http-server']}
        compute_api.firewalls().insert(project=project_id, body=firewall_body).execute()
    
    services_logtypes = {"storage.googleapis.com":"all","compute.googleapis.com":"all","logging.googleapis.com":["DATA_READ"],"iamcredentials.googleapis.com":"all"}
    confirmed = 'y' == input(
            f'Turn on audit logging for selected services {services_logtypes}? [y/n]: ').lower().strip()[0]
    if(confirmed):
        _enable_data_access_audit_logs(credentials, project_id, services_logtypes)
    


def create_app_engine():

    
    credentials, project_id = google.auth.default()
    print(f'Creating App Engine appId:{project_id}')
    app_api = discovery.build('appengine','v1', credentials=credentials)
    request_body = {"id": f"{project_id}", "locationId": "us-west2"}
    new_app = app_api.apps().create(body=request_body).execute()
    op_name = new_app['name']
    

def check_app_engine():
    found = False
    credentials, project_id = google.auth.default()
    app_api = discovery.build('appengine','v1', credentials=credentials)
    try:
        app = app_api.apps().get(appsId=project_id).execute()['name']
        found = True
    except Exception as e:
        #print(str(e))
        print('Project App Engine does not found')

    return found



def _wait_for_api_op(op_name, services_api):
    # Wait till operation finishes, giving updates every 5 seconds
    op_done = False
    t = 0
    start_time = time.time()
    time_string = ''
    while not op_done:
        time_string = f'[{int(t/60)}m {(t%60)//10}{t%10}s]'
        sys.stdout.write(
            f'\r{time_string} Enabling APIs...')
        t += 5
        while t < time.time()-start_time:
            t += 5
        time.sleep(t-(time.time()-start_time))
        # Check to see if the operation has finished
        response = services_api.operations().get(
            name=op_name).execute()
        if not 'done' in response:
            op_done = False
        else:
            op_done = response['done']
    sys.stdout.write(
        f'\r{time_string} Enabling APIs... Done\n')

def _enable_data_access_audit_logs(credentials, project_id, services_logtypes):
    new_auditConfigs=[]
    for service in services_logtypes:
        if len(services_logtypes[service]) == "all":
            auditConfig = {
                "service": service,
                "auditLogConfigs": [
                {
                    "logType": "ADMIN_READ"
                },
                {
                    "logType": "DATA_READ"
                },
                {
                    "logType": "DATA_WRITE"
                }
                ]
            }
            
        else:
            auditLogConfigs = []
            for logType in services_logtypes[service]:
                auditLogConfigs.append({ "logType": logType})
            auditConfig = {"service": service, "auditLogConfigs": auditLogConfigs}

        new_auditConfigs.append(auditConfig)

    resource = project_id
    try:
        #get current iam policy
        service = discovery.build('cloudresourcemanager', 'v1', credentials=credentials)
        get_iam_policy_request_body = {}
        current_policy = service.projects().getIamPolicy(resource=resource, body=get_iam_policy_request_body).execute()
        if "auditConfigs" in current_policy:
            auditConfigs = current_policy ["auditConfigs"].extend(new_auditConfigs)
        else:
            auditConfigs = new_auditConfigs
        
        
        set_iam_policy_request_body = {
            "policy": {
                "auditConfigs": auditConfigs
            },
            "updateMask": "auditConfigs,etag"
        }

        #print(str(set_iam_policy_request_body))
        #set iam policy to enable data access audit logs
        set_iam = service.projects().setIamPolicy(resource=resource, body=set_iam_policy_request_body).execute()
        
    except Exception as e:
        print(str(e))
    
