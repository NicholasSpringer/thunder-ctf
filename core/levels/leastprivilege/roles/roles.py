import random
import os
import re


import google.auth
from googleapiclient import discovery
from google.cloud import storage
from google.cloud import datastore

from core.framework import levels
from core.framework.cloudhelpers import deployments, iam, cloudfunctions



LEVEL_PATH = 'leastprivilege/roles'

FUNCTION_LOCATION_A = 'us-central1'
FUNCTION_LOCATION_C = 'europe-west1'


LEVEL_NAMES = {'pr':'PrimitiveRole-Project','pd1':'PredefinedRole-Storage','pd2':'PredefinedRole-Compute',
                'pd3':'PredefinedRole-Logging','pd4':'PredefinedRole-Datastore', 'pd5': 'PredefinedRole-Vision',
               'ct1':'CustomRole-Project','ct2':'CustomRole-Storage','ct3':'CustomRole-Compute','ct4':'CustomRole-Logging'
                #,'ct5': 'CustomdRole-Vision'
                }
FARS = {
         'pr':['roles/viewer'],
         'pd1':['roles/storage.objectViewer'],
         'pd2':['roles/compute.viewer'],
         'pd3':['roles/logging.viewer'],
         'pd4':['roles/datastore.viewer'],
         'pd5':['roles/datastore.user','roles/storage.admin'],
         'ct1':['storage.buckets.list','compute.instances.list'],
         'ct2':['storage.objects.list'],
         'ct3':['compute.instances.list'],
         'ct4':['logging.logEntries.list'],
         #'ct5':{'predefined':['roles/datastore.user'],'custom':['storage.buckets.get','storage.objects.create']},
         #'ct5':['datastore.entities.create','datastore.entities.get','storage.buckets.get','storage.objects.create'],
         #'ct5':['datastore.entities.create','datastore.entities.update','datastore.entities.get','datastore.entities.list','storage.buckets.get','storage.objects.create','storage.objects.delete']
        }
KINDS = ['pd4']
BUCKETS = ['pd1','ct2']
#entires created in cloud function
#F_KINDS =['pd5','ct5']
F_KINDS =['pd5']


def create(second_deploy=True):

    # Create randomized bucket name to avoid namespace conflict
    nonce = str(random.randint(100000000000, 999999999999))
    nonce_file =  f'core/levels/{LEVEL_PATH}/nonce.txt'
    #write key file in function directory
    with open(nonce_file, 'w') as f:
        f.write(nonce)
    os.chmod(nonce_file, 0o700)
    print(f'Nonce {nonce} has been written to {nonce_file}')
    

    # Set role of default cloud function account
    credentials, project_id = google.auth.default()

   
    
    print("Level initialization finished for: " + LEVEL_PATH)
    # Insert deployment
    config_template_args = {'nonce': nonce}

    template_files = [
        'core/framework/templates/service_account.jinja',
        'core/framework/templates/iam_policy.jinja',
        'core/framework/templates/bucket_acl.jinja',
        'core/framework/templates/ubuntu_vm.jinja',
        'core/framework/templates/cloud_function.jinja']


    print("Level setup started for: " + LEVEL_PATH)
    
    start_message = ' Use function entrypoints below to access levels \n\n'
    
    for RESOURCE_PREFIX in LEVEL_NAMES:

        LEVEL_NAME = LEVEL_NAMES[RESOURCE_PREFIX]
        fvar = FARS[RESOURCE_PREFIX]

        
        
        func_patha = f'core/levels/{LEVEL_PATH}/{RESOURCE_PREFIX}/functionaccess'
        func_pathc = f'core/levels/{LEVEL_PATH}/{RESOURCE_PREFIX}/functioncheck'
        
        #Generate function urls
        func_template_argc = {'fvar': fvar}
        func_upload_urla = cloudfunctions.upload_cloud_function(func_patha, FUNCTION_LOCATION_A)
        func_upload_urlc = cloudfunctions.upload_cloud_function(func_pathc, FUNCTION_LOCATION_C,template_args=func_template_argc)
       
        #Update deployment with functions
        config_template_args_patch = {f'funca_upload_url_{RESOURCE_PREFIX}':func_upload_urla, f'funcc_upload_url_{RESOURCE_PREFIX}':func_upload_urlc, 
                                       
                                        f'level_name_{RESOURCE_PREFIX}': LEVEL_NAME, f'resource_prefix_{RESOURCE_PREFIX}':RESOURCE_PREFIX }
        config_template_args.update(config_template_args_patch)

        msg= f'https://{FUNCTION_LOCATION_A}-{project_id}.cloudfunctions.net/{RESOURCE_PREFIX}-f-access-{nonce}    {LEVEL_NAMES[RESOURCE_PREFIX]}'
        start_message += msg+'\n'

    # scores funciton
    func_pathsc = f'core/levels/{LEVEL_PATH}/scores'

    #Generate scores function urls
    func_template_arg = {'anws': FARS, 'level_names':LEVEL_NAMES}
    func_upload_urlsc = cloudfunctions.upload_cloud_function(func_pathsc, FUNCTION_LOCATION_C,template_args=func_template_arg)

    login_user = os.environ.get('USER', 'USER is not set.')
    #Update deployment with functions
    config_template_args_patch = {'funcc_upload_url_scores':func_upload_urlsc, 'login_user':login_user}
    config_template_args.update(config_template_args_patch)

    msg= f'https://{FUNCTION_LOCATION_A}-{project_id}.cloudfunctions.net/scores-f-{nonce}'
    start_message += '\n Or access levels through Score Board: \n'+ msg+'\n'

    if second_deploy:
        deployments.insert(LEVEL_PATH, template_files=template_files, config_template_args=config_template_args, second_deploy=True)
    else:
        deployments.insert(LEVEL_PATH, template_files=template_files, config_template_args=config_template_args)

    try:
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
            kind =f'{k}-{nonce}-{project_id}'
            client = datastore.Client(project_id)
            for entity in entities:
                entity_key = client.key(kind)
                task = datastore.Entity(key=entity_key)
                task.update(entity)
                client.put(task)
            #print(f'Datastore {kind}  created')
    
        levels.write_start_info(LEVEL_PATH, start_message)
        
    except Exception as e: 
        exit()

def read_nonce():
    nonce_file =  f'core/levels/{LEVEL_PATH}/nonce.txt'
    level_nonce = ''
    try:
        f = open(nonce_file, "r")
        level_nonce = f.read()
    except Exception as e: 
        print(str(e))
    return level_nonce

def delete_nonce_file():
    try:
        print(f'Deleting nonce file')
        nonce_file =  f'core/levels/{LEVEL_PATH}/nonce.txt'
        if os.path.exists(nonce_file):
            os.remove(nonce_file)
    except Exception as e: 
        print(str(e))

    

def delete_custom_roles(credentials, project_id):
    service = discovery.build('iam','v1', credentials=credentials)
    parent = f'projects/{project_id}'
    try:
        response = service.projects().roles().list(parent= parent, showDeleted = False).execute()
        if 'roles' in response:
            roles = response['roles']
            if len(roles)!=0:
                print(f'Deleting custom roles ')
                NONCE = read_nonce()
                pattern = f'projects/{project_id}/roles/ct'
                for role in roles:
                    if re.search(rf"{pattern}[0-9]*_access_role_{NONCE}", role['name'], re.IGNORECASE):
                        print(role['name'])
                        try:
                            service.projects().roles().delete(name= role['name']).execute()
                        except Exception as e:
                            print('Delete error: '+str(e))
                
    except Exception as e: 
        print('Error: '+str(e))

def  delete_entities(project_id):
    print('Deleting entities')
    nonce = read_nonce()
    all_kinds = []
    all_kinds .extend(KINDS)
    all_kinds.extend(F_KINDS)
    try:
        client = datastore.Client()
        for k in all_kinds:
            kind =f'{k}-{nonce}-{project_id}'
            query = client.query(kind=kind)
            entities = query.fetch()
            for entity in entities:
                client.delete(entity.key)
    except Exception as e: 
        print(str(e))

def destroy():

    credentials, project_id = google.auth.default()
    #Delete datastore entity
    delete_entities(project_id)

    # Delete starting files
    levels.delete_start_files()

    # Delete deployment
    deployments.delete()

    delete_custom_roles(credentials, project_id)
    
    delete_nonce_file()
