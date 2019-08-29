import random
import os
import time
import sys

import jinja2
import google.auth
from googleapiclient import discovery
from googleapiclient.errors import HttpError
from . import iam, gcstorage
from .. import levels
import yaml


def _read_render_config(file_name, template_args={}):
    with open(file_name) as f:
        content = f.read()
    if not template_args == {}:
        return jinja2.Template(content).render(**template_args)
    else:
        return content


def insert(level_path, template_files=[],
           config_template_args={}, labels={}):
    '''Inserts a deployment using deployment manager, importing any specified template files. 
        If template arguments are included, the top level configuration file will be rendered using Jinja2.

    Parameters:
        level_path (str): Relative path of the level from the levels/ directory
        template_files (list of str, optional): List of paths of the template files that are used in the deployment configuration, starting with "core/".
            The names of the templates in the configuration use the filenames of the templates, not the full paths.
        config_template_args (dict, optional): Dictionary of arguments to use when rendering the top level configuration template using Jinja2.
            Keys should be strings that correspond to the names of variables in the Jinja template, and each corresponding value should be the passed value of the variable.
            If not supplied, the top level configuration will not be treated as a template.
        labels (dict, optional): Dictionary of key/value pairs that will be included as labels on the deployment, 
            and can be retrieved later using `framework.cloudhelpers.deployments.get_labels`.
            Labels are the recommended way to store any information that will be necessary for level deletion.
            The keyword "level" is reserved for storing the active level path.
    '''
    # Get current credentials from environment variables and build deployment API object
    credentials, project_id = google.auth.default()
    deployment_api = discovery.build(
        'deploymentmanager', 'v2', credentials=credentials)

    level_name = os.path.basename(level_path)
    # Create request to insert deployment
    request_body = {
        "name": "thunder",
        "target": {
            "config": {
                "content": _read_render_config(
                    f'core/levels/{level_path}/{level_name}.yaml',
                    template_args=config_template_args)
            },
            "imports": []
        },
        "labels": []
    }
    # Add imports to deployment json
    for template in template_files:
        request_body['target']['imports'].append(
            {"name": os.path.basename(template),
             "content": _read_render_config(template)})
        # If schema is present in sibling directory to template, import it
        schema_path = f'{os.path.dirname(template)}/schema/{os.path.basename(template)}.schema'
        if os.path.exists(schema_path):
            request_body['target']['imports'].append(
                {"name": os.path.basename(template) + '.schema',
                 "content": _read_render_config(schema_path)})
    # Add labels to deployment json
    for key in labels.keys():
        if key == 'level':
            exit('The label key "level" is reserved for storing the level path of the active deployment.')
        request_body['labels'].append({
            "key": key,
            "value": labels[key]
        })
    request_body['labels'].append({
        "key": 'level',
        "value": level_path.replace('/', '-')
    })
    # Send insert request then wait for operation
    operation = deployment_api.deployments().insert(
        project=project_id, body=request_body).execute()
    op_name = operation['name']
    _wait_for_operation(op_name, deployment_api,
                        project_id, level_path=level_path)


def delete():
    '''Deletes the active deployment. 
        Automatically empties and deletes any buckets in the deployment,
        and deletes all IAM bindings of service accounts in the deployment.
        This function should be called during level destruction
    '''
    _delete_resources()
    # Get current credentials from environment variables and build deployment API object
    credentials, project_id = google.auth.default()
    deployment_api = discovery.build(
        'deploymentmanager', 'v2', credentials=credentials)
    # Send delete request
    operation = deployment_api.deployments().delete(
        project=project_id, deployment='thunder').execute()
    op_name = operation['name']
    _wait_for_operation(op_name, deployment_api, project_id)


def _delete_resources():
    print('Deleting buckets and IAM entries')
    # Get current credentials from environment variables and build deployment API object
    credentials, project_id = google.auth.default()
    deployment_api = discovery.build(
        'deploymentmanager', 'v2', credentials=credentials)
    manifest_url = deployment_api.deployments().get(
        project=project_id, deployment='thunder').execute()['manifest']
    manifest_name = os.path.basename(manifest_url)
    manifest = deployment_api.manifests().get(deployment='thunder', project=project_id,
                                              manifest=manifest_name).execute()
    expanded_config = yaml.load(manifest['expandedConfig'], Loader=yaml.Loader)
    buckets = []
    service_accounts = []
    for resource in expanded_config['resources']:
        if 'type' in resource:
            if resource['type'] == 'storage.v1.bucket':
                buckets.append(resource['name'])
            if resource['type'] == 'iam.v1.serviceAccount':
                service_accounts.append(
                    iam.service_account_email(resource['name']))
    # Delete iam entries
    if service_accounts:
        iam.remove_iam_entries(service_accounts)
    # Force delete buckets
    for bucket_name in buckets:
        gcstorage.delete_bucket(bucket_name)


def _wait_for_operation(op_name, deployment_api, project_id, level_path=None):
    # Wait till  operation finishes, giving updates every 5 seconds
    op_done = False
    t = 0
    start_time = time.time()
    time_string = ''
    while not op_done:
        time_string = f'[{int(t/60)}m {(t%60)//10}{t%10}s]'
        sys.stdout.write(
            f'\r{time_string} Deployment operation in progress...')
        t += 5
        while t < time.time()-start_time:
            t += 5
        time.sleep(t-(time.time()-start_time))
        op_status = deployment_api.operations().get(
            project=project_id,
            operation=op_name).execute()['status']
        op_done = (op_status == 'DONE')
    sys.stdout.write(
        f'\r{time_string} Deployment operation in progress... Done\n')
    operation = op_status = deployment_api.operations().get(
        project=project_id,
        operation=op_name).execute()
    if 'error' in operation and level_path:
        print("\nDeployment Error:\n" + yaml.dump(operation['error']))
        if 'y' == input('\nDeployment error caused deployment to fail. '
                        'Would you like to destroy the deployment [y] or continue [n]? [y/n] ').lower().strip()[0]:
            level_module = levels.import_level(level_path)
            level_module.destroy()
            exit()


def get_labels():
    '''Queries the Deployment Manager API to retrieve the labels on the active level's deployment.

    Returns:
        dict: Dictionary of labels
    '''
    # Get current credentials from environment variables and build deployment API object
    credentials, project_id = google.auth.default()
    deployment_api = discovery.build(
        'deploymentmanager', 'v2', credentials=credentials)
    # Get deployment information
    try:
        deployment = deployment_api.deployments().get(
            project=project_id,
            deployment='thunder').execute()
    except HttpError:
        return None

    # Get labels as list of k/v pairs
    labels_list = deployment['labels']

    # Insert all k/v pairs into python dictionary
    labels_dict = {}
    for label in labels_list:
        labels_dict[label['key']] = label['value']
    labels_dict['level'] = labels_dict['level'].replace('-', '/')
    return labels_dict


def get_active_level():
    '''Returns the active level path by querying the labels of the active deployment'''
    labels = get_labels()
    if labels:
        return labels['level']
    else:
        return None
