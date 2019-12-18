import random
import os

import google.auth
from googleapiclient import discovery
from google.cloud import storage

from core.framework import levels
from core.framework.cloudhelpers import deployments, iam, gcstorage, cloudfunctions

LEVEL_PATH = 'websec/b2stuffing'
RESOURCE_PREFIX = 'b2'
INSTANCE_ZONE = 'us-west1-b'


def create():
    print("Level initialization started for: " + LEVEL_PATH)
    # Create randomized nonce name to avoid namespace conflicts
    nonce = str(random.randint(100000000000, 999999999999))
    bucket_name = f'{RESOURCE_PREFIX}-bucket-{nonce}'
    print("Level initialization finished for: " + LEVEL_PATH)
    
    source = 'core/levels/'+LEVEL_PATH+'/'
    dest='scripts/'+RESOURCE_PREFIX+'/'
    user_r, pass_r, CREDS= gen_credentials(source,dest,10,3)
    

    # Insert deployment
    config_template_args = {'nonce': nonce}
    for i in range(len(user_r)):
        kn='user_r'+str(i)
        vn=user_r[i]
        kp='pass_r'+str(i)
        vp=pass_r[i]
        config_template_args[kn]=vn
        config_template_args[kp]=vp

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
        f'Use attack.py and credentials.py to find valid credential of vulnerable websites. \nProssible credentials are {CREDS}.')
    levels.write_start_info(LEVEL_PATH, start_message)
    print(
        f'Instruction for the level can be accessed at thunder-ctf.cloud/levels/{LEVEL_PATH}.html')
    
    #move helper scripts to thunder-ctf/start
    #will fail if dicrectory start/ not being created in previous steps--examples levels.write_start_info
    #to be continue....
    
    #dest = 'start/'
    #for f in os.listdir(source):
    #    cmd='cp '+ source+f +' '+ dest+f
    #    os.popen(cmd)
        #os.replace(source+f, dest+f)
    #change permission
    #for f in os.listdir(dest):
    #    os.chmod(dest+f, 0o700)
    #remove empty helper directory
    #os.rmdir(source)

def gen_credentials(source,dest,n,m):
    
    #possible usernames
    u_srouce=source+'unames.txt'
    names=[uname.rstrip('\n') for uname in open(u_srouce,'r')]
    #most commanly used passwords
    p_srouce=source+'passwords.txt'
    passwords=[password.rstrip('\n').strip() for password in open(p_srouce,'r')]
    #randomly generate 10 credientials and write to file
    rcreds={}
    random.shuffle(names)
    random.shuffle(passwords)
    c_dest=dest+'credentials.py'
    for i in range(n):
        rcreds[names[i]]=passwords[i]
    f = open(c_dest, "w")
    f.write("creds = "+str(rcreds))
    f.close()
    #randomly generate one valid credientials
    index=random.randint(0,n-1)
    vnames=[list(rcreds.keys())[index]]
    vpass=[list(rcreds.values())[index]]
    #generate m-1 valid credientials
    for i in range(m-1):
        vnames.append(names[n+i])
        vpass.append(passwords[n+i]) 
    random.shuffle(vnames)
    random.shuffle(vpass)     
    return vnames,vpass,rcreds

def destroy():
    # Delete starting files
    levels.delete_start_files()
    # Delete deployment
    deployments.delete()
