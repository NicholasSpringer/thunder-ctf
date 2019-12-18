import random
import os

import google.auth
from googleapiclient import discovery
from google.cloud import storage

from core.framework import levels
from core.framework.cloudhelpers import deployments, iam, gcstorage, cloudfunctions

LEVEL_PATH = 'websec/b3dict'
RESOURCE_PREFIX = 'b3'
INSTANCE_ZONE = 'us-west1-b'


def create():
    print("Level initialization started for: " + LEVEL_PATH)
    # Create randomized nonce name to avoid namespace conflicts
    nonce = str(random.randint(100000000000, 999999999999))
    bucket_name = f'{RESOURCE_PREFIX}-bucket-{nonce}'
    print("Level initialization finished for: " + LEVEL_PATH)
    
    dict_size = 20
    user_r, pass_r, W_FROM, W_END = gen_credentials(dict_size)
    

    # Insert deployment
    config_template_args = {'nonce': nonce, 'user_r': user_r, 'pass_r': pass_r}

    template_files = [
        'core/framework/templates/container_vm.jinja','core/framework/templates/ubuntu_vm.jinja']
    deployments.insert(LEVEL_PATH, template_files=template_files,
                       config_template_args=config_template_args)

    print("Level setup started for: " + LEVEL_PATH)
    # Insert secret into bucket
    #storage_client = storage.Client()
    #bucket = storage_client.get_bucket(bucket_name)
    #secret_blob = storage.Blob('secret.txt', bucket)
    #secret = levels.make_secret(LEVEL_PATH)
    #secret_blob.upload_from_string(secret)

    # Create service account key file
    #sa_key = iam.generate_service_account_key(f'{RESOURCE_PREFIX}-access')

    print(f'Level creation complete for: {LEVEL_PATH}')
    start_message = (
        f'Use attack.py to find valid credential of the vulnerable website. \nYour dicrectory start from word[{W_FROM}] end at word[{W_END}]')
    levels.write_start_info(LEVEL_PATH, start_message)
    print(
        f'Instruction for the level can be accessed at thunder-ctf.cloud/levels/{LEVEL_PATH}.html')
    


def gen_credentials(n):
    
    #para n:number of words choose from in dicrectory
    import nltk
    nltk.download('words')
    from nltk.corpus import words
    w = words.words()
    l = len(w)
    #randomly generate one valid credientials
    u=random.randint(0,l-n)
    p=random.randint(u,u+n)
    vname=w[u]
    vpass=w[p]
    return vname,vpass, u, u+n

def destroy():
    # Delete starting files
    levels.delete_start_files()
    # Delete deployment
    deployments.delete()
