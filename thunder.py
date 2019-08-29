import warnings
import sys
import os
import string

from core.framework.config import cfg
from core.framework import levels, project
from core.framework.cloudhelpers import deployments

def create(*args):
    project.test_application_default_credentials()
    if len(args) != 1:
        exit(
            'Incorrect number of arguments supplied, create requires 1 argument:\n'
            'python3 thunder.py remove [level]')

    level_path = args[0]
    # Make sure a level isn't already deployed
    deployed_level = deployments.get_active_level()
    if deployed_level:
        if 'y' == input(f'Level {deployed_level} is currently deployed. '
                        f'Would you like to destroy the running instance of {deployed_level} '
                        f'and create a new instance of {level_path}? [y/n] ').lower().strip()[0]:
            destroy(confirmed=True)
            print('')
        else:
            exit()

    level_path = args[0]
    level_module = levels.import_level(level_path)
    level_module.create()


def destroy(*args, confirmed=False):
    project.test_application_default_credentials()
    if len(args) != 0:
        exit(
            'Incorrect number of arguments supplied, destroy requires no arguments:\n'
            '   python3 thunder.py destroy')
    deployed_level = deployments.get_active_level()
    if not deployed_level:
        exit(f'There is no level currently deployed')
    else:
        if not confirmed:
            if not 'y'== input(f'Destroy the running instance of {deployed_level}? [y/n] ').lower().strip()[0]:
                exit(f'{deployed_level} has not been destroyed.')

    level_module = levels.import_level(deployed_level)
    level_module.destroy()


def list_available_levels(*args):
    print([key for key in cfg.get_seeds().keys()])


def get_active_level(*args):
    project.test_application_default_credentials()
    print(deployments.get_active_level())


def add_levels(*args):
    if len(args) == 0:
        exit(
            'Incorrect number of arguments supplied, activate_project requires at least 1 argument:\n'
            '   python3 thunder.py add_levels [level-path] [level-path]...')
    for level_path in args:
        # Check to make sure level path only contains allowed characters
        allowed = string.ascii_lowercase + string.digits + '_' +'/'
        if not all(c in allowed for c in level_path):
            exit('Level paths can only contain lowercase letters, numeric characters, slashes, and underscores.')
        levels.add_level(level_path)


def activate_project(*args):
    if len(args) != 1:
        exit(
            'Incorrect number of arguments supplied, activate_project requires 1 argument:\n'
            '   python3 thunder.py activate_project [project-id]')
    project_id = args[0]
    confirmed = 'y' == input(
                f'Set project to {project_id}? The CTF should be run on a new project with no infrastructure. [y/n]: ').lower().strip()[0]
    if(confirmed):
        # Make sure credentials are set correctly and have owner role
        project.test_application_default_credentials(tctf_project=project_id)
        # Enable apis, grant DM service account owner status
        project.setup_project()
        # Set project in thunder ctf config
        cfg.set_project(project_id)
        print('Project has been set.')
    else:
        print('Project not set.')


def generate_level_docs():
    levels.generate_level_docs()


def help(*args):
    print("""Available commands:
    python3 thunder.py create [level]
    python3 thunder.py destroy
    python3 thunder.py list_available_levels
    python3 thunder.py get_active_level
    python3 thunder.py activate_project [project-id]
    python3 thunder.py help

Developer commands:
    python3 thunder.py add_levels [level-path] [level-path]...
    python3 thunder.py generate_level_docs
    """)
    exit()


if __name__ == '__main__':
    warnings.filterwarnings("ignore", module="google.auth")
    os.chdir(os.getcwd()+'/'+os.path.dirname(__file__))
    # python3 thunder.py action [args]
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
