import json
import importlib
import os


def import_level(level_name):
    # Check if level is in level-list.txt
    with open('core/levels/level-list.txt') as f:
        level_names = f.read().split('\n')
    if not level_name in level_names:
        raise Exception(
            f'Level: {level_name} not found in levels list. If the spelling is correct, '
            'make sure the level is present in levels/level-list.txt')
    # Check if level secret has been generated
    with open('core/common/seeds.json') as f:
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


def write_start_file(file_name, file_content):
    file_path = f'start-info/{file_name}'
    print(
        f'\nStarting file: {file_name} has been written to {file_path}\n')

    with open(file_path, 'w+') as f:
        f.write(file_content)
    os.chmod(file_path, 0o400)


def delete_start_file(file_name):
    file_path = f'start-info/{file_name}'
    if os.path.exists(file_path):
        os.chmod(file_path, 0o700)
        os.remove(file_path)
