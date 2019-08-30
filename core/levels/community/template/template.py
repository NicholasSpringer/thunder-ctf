from core.framework import levels
from core.framework.cloudhelpers import deployments

LEVEL_PATH = 'community/template'


def create():
    # Don't deploy the template. Delete this line when you implement your level.
    exit('This is a template file. It is not meant to be deployed.')

    # ---------Level Initialization---------
    # Put code here that generates anything passed to the configuration template,
    # sets up the project before deployment, or does anything else that happens
    # before the deployment gets inserted.

    # --------------------------------------

    # ---------Deployment Insertion---------
    # Insert the deployment, filling out labels, config template arguments,
    # and the deployment manager template imports.
    config_template_args = {}
    labels = {}
    template_files = []
    deployments.insert(LEVEL_PATH,
                       config_template_args=config_template_args,
                       labels=labels,
                       template_files=template_files)
    # --------------------------------------

    # --------------Level Setup-------------
    # Put code here that does anything that needs to happen after the deployment.
    # This includes usings APIs to modify deployed resources or anything else.

    # Print complete message and print/save start info
    print(f'Level creation complete for: {LEVEL_PATH}\n'
          f'Instruction for the level can be accessed at '
          f'thunder-ctf.cloud/levels/{LEVEL_PATH}.html')
    start_message = '--Put the start message here.--'
    levels.write_start_info(LEVEL_PATH, start_message)
    # --------------------------------------


def destroy():
    # If necessary, put code here that resets anything 
    # that the deployment manager won't delete

    # Delete starting files
    levels.delete_start_files()
    # Delete deployment
    deployments.delete()
