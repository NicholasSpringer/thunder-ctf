import json
import importlib
import os
import random
import hashlib
import shutil

import google.auth
from jinja2 import Template

from .config import cfg


def import_level(level_path):
    '''Returns the imported python module of the given level path.

    Parameters:
        level_path (str): Relative path of level from core/levels/ directory
    
    Returns:
        module: The python module of the given level
    '''
    # Check if level is in config
    if not level_path in cfg.get_seeds():
        exit(
            f'Level: {level_path} not found in levels list. A list of available levels can be found by running:\n'
            '  python3 thunder.py list_levels\n'
            'If this is a custom level that you have not yet imported, run:\n'
            '  python3 thunder.py add_levels [level-path]')

    level_name = os.path.basename(level_path)
    try:
        level_module = importlib.import_module(
            f'.levels.{level_path.replace("/", ".")}.{level_name}', package='core')
    except ImportError:
        raise ImportError(
            f'Cannot import level: {level_path}. Check above error for details.')
    return level_module


def add_level(level_path):
    '''Generates a seed for a new level, which is necessary to generate level secrets.

    Parameters:
        level_path (str): The path of the level
    '''
    # Check to see if level already has a seed
    if level_path in cfg.get_seeds():
        exit(f'{level_path} has already been imported.')
    # Check to see if level has the necessary files
    level_name = os.path.basename(level_path)
    level_py_path = f'core/levels/{level_path}/{level_name}.py'
    level_yaml_path = f'core/levels/{level_path}/{level_name}.yaml'
    if not os.path.exists(level_py_path):
        exit(f'Expected level python file was not found at {level_py_path}')
    if not os.path.exists(level_yaml_path):
        exit(
            f'Expected yaml configuration file was not found at {level_yaml_path}')
    # Generate a random seed for the specified level
    seeds = cfg.get_seeds()
    seeds[level_path] = str(random.randint(100000, 999999))
    cfg.set_seeds(seeds)


def make_secret(level_path, chars=None):
    '''Generates the secret of the level by hashing the level seed and the player's project id.

    Parameters:
        level_path (str): The path of the level
        chars (int, optional): Integer that sets the length of the returned secret. If not supplied, the secret will be arbitrary length based on the value of the hash.

    Returns:
        str: String that contains an integer version of the hash of the level seed and project id 
    '''
    credentials, project_id = google.auth.default()
    seeds = cfg.get_seeds()
    seed = seeds[level_path]
    if(not chars):
        return str(int(hashlib.sha1((seed+project_id).encode('utf-8')).hexdigest(), 16))
    else:
        return str(int(hashlib.sha1((seed+project_id).encode('utf-8')).hexdigest(), 16))[:chars]


def write_start_info(level_path, message, file_name=None, file_content=None):
    '''Prints the start message and saves start files.
    
    Prints the supplied start message and saves it to a text file, and saves another optional file, which can be used for credential files, ssh key files, or any other file that the player is given at the beginning of the level. This function saves files in the start/ directory.

    Parameters:
        level_path (str): The path of the level being created
        message (str): The start message that will be printed and saved
        file_name (str, optional): The name of the optional extra file
        file_content (str, optional): The contents of the optional extra file
    '''
    print('\n')
    # If start directory is not present, create it
    if not os.path.exists('start'):
        os.makedirs('start')
    # If there is an extra file, create it
    if file_name and file_content:
        file_path = f'start/{file_name}'
        with open(file_path, 'w+') as f:
            f.write(file_content)
        os.chmod(file_path, 0o400)
        print(
            f'Starting file: {file_name} has been written to {file_path}')
    # Write the start message to a file 
    level_name = os.path.basename(level_path)
    message_file_path = f'start/{level_name}.txt'
    with open(message_file_path, 'w+') as f:
        f.write(message)
    os.chmod(message_file_path, 0o400)
    print(
        f'Starting message for {level_path} has been written to {message_file_path}')
    # Print start message
    print(f'Start Message: {message}')
    print('\n')


def delete_start_files():
    '''Deletes the start files of a level. This function should be called upon level destruction.'''
    shutil.rmtree('start')


def generate_level_docs():
    '''Generates HTML documents for each level based on each level's [levelname].hints.html'''
    with open('core/framework/level-hints-template.jinja') as f:
        template = Template(f.read())

    for level_path in cfg.get_seeds():
        level_name = os.path.basename(level_path)
        if os.path.exists(f'core/framework/config/project.txt'):
            with open(f'core/levels/{level_path}/{level_name}.hints.html') as f:
                # Split hints in file
                blocks = f.read().split('\n---\n')
            # Set jinja args, indenting html tags that are mnot on the first line
            jinja_args = {'level_path': level_path,
                          'intro': blocks[0].replace('\n<', f'\n{" "*6}<'),
                          'hints': [block.replace('\n<', f'\n{" "*6}<') for block in blocks[1:-1]],
                          'writeup': blocks[-1].replace('\n<', f'\n{" "*4}<')}

            render = template.render(**jinja_args)
            if not os.path.exists(f'docs/{os.path.dirname(level_path)}'):
                os.makedirs(f'docs/{os.path.dirname(level_path)}')
            with open(f'docs/{level_path}.html', 'w+') as f:
                f.write(render)
        else:
            print(
                f'No hints file found for level: {level_path} at core/framework/config/project.txt')
