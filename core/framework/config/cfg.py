import os
import json

def get_seeds():
    '''Returns a dictionary where the keys are the imported levels, and the values are the corresponding seeds used for generating secrets.'''
    if not os.path.exists('core/framework/config/seeds.json'):
        return {}
    else:
        with open('core/framework/config/seeds.json') as f:
            return json.loads(f.read())

def set_seeds(seeds_dict):
    '''Sets the contents of "seeds.json" with the given dictionary'''
    with open('core/framework/config/seeds.json','w+') as f:
        f.write(json.dumps(seeds_dict))

def get_project():
    '''Returns the project in the thunder ctf configuration, which is stored in "project.txt"'''
    if not os.path.exists('core/framework/config/project.txt'):
        return ''
    else:
        with open('core/framework/config/project.txt') as f:
            return f.read()

def set_project(project_id):
    '''Sets the project in the thunder ctf configuration, which is stored in "project.txt"'''
    with open('core/framework/config/project.txt','w+') as f:
        f.write(project_id)