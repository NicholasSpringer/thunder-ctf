import json
import importlib
import os


def import_level(level_name):
    # Check if level is in level-list.txt
    with open('core/common/config/level-list.txt') as f:
        level_names = f.read().split('\n')
    if not level_name in level_names:
        raise Exception(
            f'Level: {level_name} not found in levels list. If the spelling is correct, '
            'make sure the level is present in core/common/config/level-list.txt')
    # Check if level secret has been generated
    with open('core/common/config/seeds.json') as f:
        seeds = json.loads(f.read())
    if not level_name in seeds.keys():
        raise Exception(
            f'Level seed has not been generated for Level: {level_name}. '
            'If you wish to generate a new seed, run new_seeds:\n'
            f'  python3 gcp-vulnerable.py new_seeds {level_name}')

    try:
        level_module = importlib.import_module(
            f'.levels.{level_name}.{level_name}', package='core')
    except ImportError:
        raise ImportError(f'Cannot import level: {level_name}. '
                          'Check to ensure its python file is present at '
                          'core/levels/[level-name]/[level-name].py')

    return level_module


def write_start_info(level_name, message, file_name=None, file_content=None):
    print('\n')
    if not os.path.exists('start-info'):
            os.makedirs('start-info')
    if file_name and file_content:
        file_path = f'start-info/{file_name}'
        with open(file_path, 'w+') as f:
            f.write(file_content)
        os.chmod(file_path, 0o400)
        print(
            f'Starting file: {file_name} has been written to {file_path}')
    message_file_path = f'start-info/{level_name}.txt'
    with open(message_file_path, 'w+') as f:
        f.write(message)
    os.chmod(message_file_path, 0o400)
    print(
        f'Starting message for {level_name} has been written to {file_path}')
    print(f'Start Message: {message}')
    print('\n')

def delete_start_files(level_name, files=[]):
    files.append(f'{level_name}.txt')
    for f in files:
        file_path = f'start-info/{f}'
        if os.path.exists(file_path):
            os.chmod(file_path, 0o700)
            os.remove(file_path)
