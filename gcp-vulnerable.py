import warnings
import sys

from core.common import secrets, deployments
from core.common.importlevels import import_level

warnings.filterwarnings("ignore", module="google.auth")


def create(*args):
    if len(args) != 1:
        raise Exception(
            'Incorrect number of arguments supplied, create requires 1 argument:\n'
            'python3 gcp-vulnerable.py remove [level]')

    level_name = args[0]
    level_module = import_level(level_name)
    level_module.create()


def destroy(*args):
    if len(args) != 1:
        raise Exception(
            'Incorrect number of arguments supplied, destroy requires 1 argument:\n'
            '   python3 gcp-vulnerable.py destroy [level]')

    level_name = args[0]
    level_module = import_level(level_name)
    level_module.destroy()


def list_levels():
    with open('core/levels/level-list.txt') as f:
        print(f.read())


def list_active_levels():
    print(deployments.list_deployments())


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


def help():
    print("""Available commands:
    python3 gcp-vulnerable.py create [level]
    python3 gcp-vulnerable.py destroy [level]
    python3 gcp-vulnerable.py help""")
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
