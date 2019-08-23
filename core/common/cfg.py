import os
import json

def get_config():
    if not os.path.exists('core/common/config.json'):
        with open('core/common/config.json','w+') as f:
            f.write(json.dumps({}))
        return {}
    with open('core/common/config.json') as f:
        return json.loads(f.read())

def set_config(config):
    with open('core/common/config.json','w+') as f:
        f.write(json.dumps(config))