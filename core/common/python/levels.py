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


def get_start_info(level_name):
    file_path = f'start-info/{level_name}.txt'
    if not os.path.exists(file_path):
        exit('Start info file cannot be found. Reload the level to get a new file.')
    with open(file_path) as f:
        info = f.read()
    print(f'Starting information for {level_name}:\n\n' + info)


def log_start_info(level_name, info):
    file_path = f'start-info/{level_name}.txt'
    print(f'Starting information for {level_name}:\n\n' + info +
          f'\n\nStarting information can always be retrieved from /{file_path}, or by running:\n',
          f'  python3 thunder.py get_start_info {level_name}')

    with open(file_path, 'w+') as f:
        f.write(info)
    os.chmod(file_path, 0o400)


def delete_start_info(level_name):
    file_path = f'start-info/{level_name}.txt'
    os.chmod(file_path, 0o700)
    os.remove(file_path)
