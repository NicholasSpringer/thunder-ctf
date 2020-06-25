import random
import os
import re

import google.auth
from googleapiclient import discovery
from google.cloud import storage
from google.cloud import datastore

from core.framework import levels
from core.framework.cloudhelpers import deployments, iam, cloudfunctions

from cryptography.fernet import Fernet

LEVEL_PATH = 'leastprivilege/roles'
#RESOURCE_PREFIX = 'c6'
FUNCTION_LOCATION = 'us-central1'
#LEVEL_NAME ='project'
LEVEL_NAMES = {'pd1':'Storage','pd2':'Compute','pd3':'Logging','pd4':'Datastore','ct1':'Projects','ct2':'Storage','ct3':'Compute','ct4':'Logging'}
fvars = {
         'pd1':'roles/storage.objectViewer',
         'pd2':'roles/compute.viewer',
         'pd3':'roles/logging.viewer',
         'pd4':'roles/datastore.viewer',
         'ct1':['storage.buckets.list','compute.instances.list'],
         'ct2':['storage.buckets.list'],
         'ct3':['compute.instances.list'],
         'ct4':['logging.logEntries.list']
         

        }
KINDS = {'pd4':''}
BUCKETS = ['pd1','ct2']

def create():

    # Create randomized bucket name to avoid namespace conflict
    nonce = str(random.randint(100000000000, 999999999999))
    
    

    # Set role of default cloud function account
    credentials, project_id = google.auth.default()

   
    
    print("Level initialization finished for: " + LEVEL_PATH)
    # Insert deployment
    config_template_args = {'nonce': nonce}

    template_files = [
        'core/framework/templates/service_account.jinja',
        'core/framework/templates/iam_policy.jinja',
        'core/framework/templates/bucket_acl.jinja',
        'core/framework/templates/ubuntu_vm.jinja']

    deployments.insert(LEVEL_PATH, template_files=template_files,
                       config_template_args=config_template_args)

    print("Level setup started for: " + LEVEL_PATH)
    
    # Insert secret into bucket
    storage_client = storage.Client()
    for b in BUCKETS:
        bucket_name = f'{b}-bucket-{nonce}'
        secret = levels.make_secret(LEVEL_PATH)
        bucket = storage_client.get_bucket(bucket_name)
        secret_blob = storage.Blob(f'secret_{b}.txt', bucket)
        secret_blob.upload_from_string(secret)

    

    # Create and insert data in datastore
    for k in KINDS:
        entities =[{'name': f'admin-{k}','password': 'admin1234','active': True},{'name': f'editor-{k}','password': '1111','active': True}]
        KIND=f'{k}-Users-{nonce}-{project_id}'
        KINDS[k]=KIND
        client = datastore.Client(project_id)
        for entity in entities:
            entity_key = client.key(KINDS[k])
            task = datastore.Entity(key=entity_key)
            task.update(entity)
            client.put(task)
        print(f'Datastore {KIND}  created')


    
    template_files_patch = ['core/framework/templates/cloud_function.jinja']
    template_files.extend(template_files_patch)
    

    for RESOURCE_PREFIX in LEVEL_NAMES:

        LEVEL_NAME = LEVEL_NAMES[RESOURCE_PREFIX]
        fvar = fvars[RESOURCE_PREFIX]

        #print(f'Level creation for: {LEVEL_PATH}/{RESOURCE_PREFIX}/{LEVEL_NAME}')
        #Generate account key files
        sa_keya = iam.generate_service_account_key(f'{RESOURCE_PREFIX}-access')
        sa_keyc = iam.generate_service_account_key(f'{RESOURCE_PREFIX}-check')
        
        func_patha = f'core/levels/{LEVEL_PATH}/{RESOURCE_PREFIX}/functionaccess'
        func_pathc = f'core/levels/{LEVEL_PATH}/{RESOURCE_PREFIX}/functioncheck'
        func_namea = f'{func_patha}/{RESOURCE_PREFIX}-access.json'
        func_namec = f'{func_pathc}/{RESOURCE_PREFIX}-check.json'

        #write key file in function directory
        with open(func_namea, 'w') as f:
            f.write(sa_keya)
        os.chmod(func_namea, 0o700)
        print(f'Key file: {RESOURCE_PREFIX}-access has been written to {func_namea}')
        with open(func_namec, 'w') as f:
            f.write(sa_keyc)
        os.chmod(func_namec, 0o700)
        print(f'Key file: {RESOURCE_PREFIX}-check has been written to {func_namec}')
        
        #Generate function urls
        func_template_argsc = {'fvar': fvar}
        func_upload_urla = cloudfunctions.upload_cloud_function(func_patha, FUNCTION_LOCATION)
        func_upload_urlc = cloudfunctions.upload_cloud_function(func_pathc, FUNCTION_LOCATION,template_args=func_template_argsc)
        #print(func_upload_urla)
        #Update deployment with functions
        config_template_args_patch = {f'funca_upload_url_{RESOURCE_PREFIX}':func_upload_urla, f'funcc_upload_url_{RESOURCE_PREFIX}':func_upload_urlc, 
                                       
                                        f'level_name_{RESOURCE_PREFIX}': LEVEL_NAME, f'resource_prefix_{RESOURCE_PREFIX}':RESOURCE_PREFIX }
        config_template_args.update(config_template_args_patch)
        
        
    deployments.patch(LEVEL_PATH, template_files=template_files, config_template_args=config_template_args)

    print('Patching completed')
    print( 'Use function entrypoints below to access levels:')
    for RESOURCE_PREFIX in LEVEL_NAMES:
        # temp datastore permissions not supported for custom roles, will explore other Native  mode
        print(f'https://{FUNCTION_LOCATION}-{project_id}.cloudfunctions.net/{RESOURCE_PREFIX}-f-access-{nonce}')

def create_appeng():
    found = False
    credentials, project_id = google.auth.default()
    app_api = discovery.build('appengine','v1', credentials=credentials)
    try:
        app = app_api.apps().get(appsId=project_id).execute()['name']
        found = True
    except Exception as e:
        #print(str(e))
        print('Project App Engine does not found')

    if not found:
        print(f'Creating App Engine appId:{project_id}')
        request_body = {"id": f"{project_id}", "locationId": "us-west2"}
        new_app = app_api.apps().create(body=request_body).execute()

def delete_custom_roles():
    print(f'Deleting custom roles')
    credentials, project_id = google.auth.default()
    service = discovery.build('iam','v1', credentials=credentials)
    parent = f'projects/{project_id}'
    try:
        roles = service.projects().roles().list(parent= parent, showDeleted = False).execute()['roles']
        if len(roles)!=0:
            pattern = f'projects/{project_id}/roles/ct'
            for role in roles:
                if re.search(rf"{pattern}[0-9]_access_role_", role['name'], re.IGNORECASE):
                    service.projects().roles().delete(name= role['name']).execute()
    except Exception as e: 
        print(str(e))


       



def destroy():
    #Delete datastore
    print('Deleting entities')
    try:
        client = datastore.Client()
        for k in KINDS:
            query = client.query(kind=KINDS[k])
            entities = query.fetch()
            for entity in entities:
                client.delete(entity.key)
    except Exception as e: 
        print(str(e))


    # Delete starting files
    levels.delete_start_files()
    print(f'Deleting json key files')
    for RESOURCE_PREFIX in LEVEL_NAMES:
        actpatha=f'core/levels/{LEVEL_PATH}/{RESOURCE_PREFIX}/functionaccess/{RESOURCE_PREFIX}-access.json'
        # Delete key files
        if os.path.exists(actpatha):
            os.remove(actpatha)
        actpathc=f'core/levels/{LEVEL_PATH}/{RESOURCE_PREFIX}/functioncheck/{RESOURCE_PREFIX}-check.json'
        if os.path.exists(actpathc):
            os.remove(actpathc)

    # Delete deployment
    deployments.delete()
    delete_custom_roles()
    

