import warnings
import sys
import os

from core.common.python import secrets, deployments, levels, cloudresources


def create(*args):
    cloudresources.test_application_default_credentials()
    if len(args) != 1:
        exit(
            'Incorrect number of arguments supplied, create requires 1 argument:\n'
            'python3 thunder.py remove [level]')

    level_name = args[0]
    # Make sure level isn't already deployed
    if level_name in deployments.list_deployments():
        exit(f'Level {level_name} has already been deployed. '
             'To reload the level, first destroy the running deployment.')

    level_name = args[0]
    level_module = levels.import_level(level_name)
    level_module.create()


def destroy(*args):
    cloudresources.test_application_default_credentials()
    if len(args) != 1:
        exit(
            'Incorrect number of arguments supplied, destroy requires 1 argument:\n'
            '   python3 thunder.py destroy [level]')
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
    cloudresources.test_application_default_credentials()
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
        print('Seeds generated.')
    else:
        print('No seeds generated.')


def set_project(*args):
    if len(args) != 1:
        exit(
            'Incorrect number of arguments supplied, set_project requires 1 argument:\n'
            '   python3 thunder.py set_project [project-id]')
    project_id = args[0]
    confirmed = 'y' == input(
                f'Set project to {project_id}? If {project_id} has existing cloud infrastructure, it may be disrupted. [y/n]: ').lower()[0]
    if(confirmed):
        # Make sure credentials are set correctly and have owner role
        cloudresources.test_application_default_credentials(set_project=project_id)
        # Enable apis, grant DM owner status, etc
        cloudresources.setup_project()
        with open('core/common/config/project.txt','w+') as f:
            f.write(project_id)
        print('Project has been set.')
    else:
        print('Project not set.')


def help(*args):
    print("""Available commands:
    python3 thunder.py create [level]
    python3 thunder.py destroy [level]
    python3 thunder.py help
    python3 thunder.py list_levels
    python3 thunder.py list_active_levels
    python3 thunder.py set_project [project-id]""")
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
