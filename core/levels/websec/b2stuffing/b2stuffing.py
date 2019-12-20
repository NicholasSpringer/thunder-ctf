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
LEVEL_NAME ='b2stuffing'
CRED_PATH='scripts/'+RESOURCE_PREFIX+'/'
#Max number of instances can be max(#passwords.txt, #unames.txt)-len(RCREDS)
NUM_OF_CONTAINERS = 3
SOURCE = 'core/levels/'+LEVEL_PATH+'/'

def create():
    print("Level initialization started for: " + LEVEL_PATH)
    # Create randomized nonce name to avoid namespace conflicts
    nonce = str(random.randint(100000000000, 999999999999))
    bucket_name = f'{RESOURCE_PREFIX}-bucket-{nonce}'
    print("Level initialization finished for: " + LEVEL_PATH)
       
    
    vcreds, RCREDS= gen_credentials(SOURCE,CRED_PATH,10,NUM_OF_CONTAINERS)
    
    #Prepare args and yaml
    container_yaml = SOURCE+'container.yaml'  
    conyaml = open(container_yaml,'r')
    container = conyaml.read()
    conyaml.close()
    
    attack_yaml = SOURCE+'attack.yaml'
    attyaml = open(attack_yaml,'r')
    attack = attyaml.read()
    attyaml.close()
    
    level_yaml = SOURCE+LEVEL_NAME+'.yaml'
    levyaml = open(level_yaml,'a')
    levyaml.write(attack)   

    config_template_args = {'nonce': nonce}
    
    for i in range(NUM_OF_CONTAINERS):
        kn='user_r'+str(i)
        vn=list(vcreds[i].keys())[0]
        kp='pass_r'+str(i)
        vp=list(vcreds[i].values())[0]
        config_template_args[kn]=vn
        config_template_args[kp]=vp
        levyaml.write(container.replace('{UUU}',kn).replace('{PPP}',kp).replace('{INDEX}',str(i)))
    levyaml.close()
    
    # Insert deployment
    template_files = [
        'core/framework/templates/container_vm.jinja','core/framework/templates/ubuntu_vm.jinja']
    deployments.insert(LEVEL_PATH, template_files=template_files,
                       config_template_args=config_template_args)

    print("Level setup started for: " + LEVEL_PATH)

    print(f'Level creation complete for: {LEVEL_PATH}')
    start_message = (
        f'Use attack.py and credentials.py to find valid credential of vulnerable websites. \nProssible credentials are {RCREDS}.')
    levels.write_start_info(LEVEL_PATH, start_message)
    print(
        f'Instruction for the level can be accessed at thunder-ctf.cloud/levels/{LEVEL_PATH}.html')

def gen_credentials(source,dest,n,m):
    
    #Possible usernames
    u_srouce=source+'unames.txt'
    names=[uname.rstrip('\n') for uname in open(u_srouce,'r')]
    #Most commanly used passwords
    p_srouce=source+'passwords.txt'
    passwords=[password.rstrip('\n').strip() for password in open(p_srouce,'r')]
    #Randomly generate 10 credientials and write to file
    rcreds={}
    random.shuffle(names)
    random.shuffle(passwords)
    c_dest=dest+'credentials.py'
    for i in range(n):
        rcreds[names[i]]=passwords[i]
    f = open(c_dest, "w")
    f.write("creds = "+str(rcreds))
    f.close()
    #Randomly generate one valid credientials
    index=random.randint(0,n-1)
    vcreds=[{list(rcreds.keys())[index] : list(rcreds.values())[index]}]
    #Generate m-1 valid credientials
    for i in range(m-1): 
        vcreds.append({names[n+i]:passwords[n+i]}) 
    random.shuffle(vcreds)     
    return vcreds,rcreds

def destroy():
    # Delete starting files
    levels.delete_start_files()
    # Delete credentials.py
    if os.path.exists(CRED_PATH+'credentials.py'):
        os.remove(CRED_PATH+'credentials.py')
    # Empty level yaml file
    level_yaml = SOURCE+LEVEL_NAME+'.yaml'
    open(level_yaml, 'w').close()
    # Delete deployment
    deployments.delete()
