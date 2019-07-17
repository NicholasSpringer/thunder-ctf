import json
import random
import hashlib
import warnings
import os

import google.auth


def generate_seeds(level_names=[]):
    # Generate new random seeds for each level in level list
    # by default, reset all seeds in level-list
    if level_names==[]:
        with open('core/levels/level-list.txt') as f:
            level_names = f.read().split('\n')
    
    with open('core/common/seeds.json') as f:
        seeds = json.loads(f.read())
    for level_name in level_names:
        seeds[level_name] = str(random.randint(100000, 999999))
    # Write to seeds json file
    with open('core/common/seeds.json', "w+") as f:
        f.write(json.dumps(seeds))
    print(f'New seeds have been generated for {level_names}')


def make_secret(level_name):
    credentials, project_id = google.auth.default()
    with open('core/common/seeds.json') as f:
        seeds = json.loads(f.read())
    seed = seeds[level_name]
    return hashlib.sha1((seed+project_id).encode('utf-8')).hexdigest()


if __name__ == '__main__':
    generate_seeds()
