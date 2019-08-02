import warnings
import sys

from core.common.python import secrets, deployments, levels


warnings.filterwarnings("ignore", module="google.auth")


def create(*args):
    if len(args) != 1:
        exit(
            'Incorrect number of arguments supplied, create requires 1 argument:\n'
            'python3 gcp-vulnerable.py remove [level]')

    level_name = args[0]
    # Make sure level isn't already deployed
    if level_name in deployments.list_deployments():
        exit(f'Level {level_name} has already been deployed. '
             'To reload the level, first destroy the running deployment.')

    level_name = args[0]
    level_module = levels.import_level(level_name)
    level_module.create()


def destroy(*args):
    if len(args) != 1:
        exit(
            'Incorrect number of arguments supplied, destroy requires 1 argument:\n'
            '   python3 gcp-vulnerable.py destroy [level]')
    level_name = args[0]
    # Make sure level is deployed
    if not level_name in deployments.list_deployments():
        exit(f'Level {level_name} is not currently deployed')

    level_module = levels.import_level(level_name)
    level_module.destroy()


def list_levels(*args):
    with open('core/levels/level-list.txt') as f:
        print(f.read())


def list_active_levels(*args):
    print(deployments.list_deployments())

def get_start_info(*args):
    if len(args) != 1:
        exit(
            'Incorrect number of arguments supplied, get_start_info requires 1 argument:\n'
            '   python3 gcp-vulnerable.py get_start_info [level]')
    level_name = args[0]
    if not level_name in deployments.list_deployments():
        exit(f'Level {level_name} is not currently deployed')
    


def new_seeds(*args):
    confirmed = False
    if len(args) == 0:
        if 'y' == input(
                'Generate new seeds for all levels? Level secrets will differ from expected values. [y/n]').lower()[0]:
            confirmed = True
    else:
        if'y' == input(
                f'Generate new seeds for {list(args)}? Level secrets will differ from expected values. [y/n]').lower()[0]:
            confirmed = True
    if confirmed:
        secrets.generate_seeds(level_names=list(args))


def help(*args):
    print("""Available commands:
    python3 thunder.py create [level]
    python3 thunder.py destroy [level]
    python3 thunder.py help
    python3 thunder.py list_levels
    python3 thunder.py list_active_levels""")
    exit()


if __name__ == '__main__':
    # python3 gcp-vulnerable.py action [args]
    args = sys.argv[1:]
    if len(args) == 0:
        action = 'help'
    else:
        action = args[0]

    try:
        func = locals()[action]
        if not callable(func):
            raise KeyError
    except KeyError:
        func = help
    func(*args[1:])
