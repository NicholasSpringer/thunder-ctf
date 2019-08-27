import os
import json

def get_seeds():
    if not os.path.exists('core/common/config/seeds.json'):
        return {}
    else:
        with open('core/common/config/seeds.json') as f:
            return json.loads(f.read())

def set_seeds(seeds_dict):
    with open('core/common/config/seeds.json','w+') as f:
        f.write(json.dumps(seeds_dict))

def get_project():
    if not os.path.exists('core/common/config/project.txt'):
        return ''
    else:
        with open('core/common/config/project.txt') as f:
            return f.read()

def set_project(project_id):
    with open('core/common/config/project.txt','w+') as f:
        f.write(project_id)