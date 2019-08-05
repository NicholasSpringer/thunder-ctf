import random
import os
import time

import google.auth
from googleapiclient import discovery
from . import cloudresources


def read_config(file_name, config_properties={}):
    with open(file_name) as f:
        content = f.read()
    for key in config_properties.keys():
        content = content.replace('//'+key+'//', config_properties[key])
    return content


def insert(level_name, template_files=[],
           config_properties={}, labels={}):
    # Get current credentials from environment variables and build deployment API object
    credentials, project_id = google.auth.default()
    deployment_api = discovery.build(
        'deploymentmanager', 'v2', credentials=credentials)

    # Create request to insert deployment
    request_body = {
        "name": level_name,
        "target": {
            "config": {
                "content": read_config(
                    f'core/levels/{level_name}/{level_name}.yaml',
                    config_properties=config_properties)
            },
            "imports": []
        },
        "labels": []
    }
    # Add imports to deployment json
    for template in template_files:
        template_file = 'core/' + template
        schema_file = f'core/{os.path.dirname(template)}/schema/{os.path.basename(template)}.schema'
        request_body['target']['imports'].extend([
            {"name": os.path.basename(template),
             "content": read_config(template_file)},
            {"name": os.path.basename(template) + '.schema',
             "content": read_config(schema_file)}])
    # Add labels to deployment json
    for key in labels.keys():
        request_body['labels'].append({
            "key": key,
            "value": labels[key]
        })
    # Send insert request, get operation name
    operation = deployment_api.deployments().insert(
        project=project_id, body=request_body).execute()
    op_name = operation['name']
    # If error occurred in deployment, raise it
    if 'error' in operation.keys():
        raise Exception(operation['error'])
    print('Deployment insertion started.')
    wait_for_operation(op_name, deployment_api, project_id)
    print('Deployment insertion finished.')


def delete(level_name, buckets=[], service_accounts=[]):
    print('Level destruction started for: ' + level_name)
    # Delete iam entries
    if not service_accounts == []:
        cloudresources.remove_accounts_iam(service_accounts)
    # Force delete buckets
    for bucket_name in buckets:
        cloudresources.delete_bucket(bucket_name)

    # Get current credentials from environment variables and build deployment API object
    credentials, project_id = google.auth.default()
    deployment_api = discovery.build(
        'deploymentmanager', 'v2', credentials=credentials)
    # Send delete request
    operation = deployment_api.deployments().delete(
        project=project_id, deployment=level_name).execute()
    op_name = operation['name']
    # If error occurred in deployment, raise it
    if 'error' in operation.keys():
        raise Exception(operation['error'])
    print('Deployment deletion started.')
    wait_for_operation(op_name, deployment_api, project_id)
    print('Deployment deletion finished.')


def get_labels(level_name):
    # Get current credentials from environment variables and build deployment API object
    credentials, project_id = google.auth.default()
    deployment_api = discovery.build(
        'deploymentmanager', 'v2', credentials=credentials)
    # Get deployment information
    deployment = deployment_api.deployments().get(
        project=project_id,
        deployment=level_name).execute()

    # If deployment has labels, get labels as list of k/v pairs
    labels_list = []
    if 'labels' in deployment.keys():
        labels_list = deployment['labels']

    # Insert all k/v pairs into python dictionary
    labels_dict = {}
    for label in labels_list:
        labels_dict[label['key']] = label['value']
    return labels_dict


def wait_for_operation(op_name, deployment_api, project_id):
    # Wait till  operation finishes, giving updates every 5 seconds
    op_status = 'STARTING'
    t = 0
    while op_status != 'DONE':
        print(f'[{int(t/60)}m {t%60}s] '
              f'Deployment operation in progress. Status: {op_status}')
        time.sleep(5)
        t += 5
        op_status = deployment_api.operations().get(
            project=project_id,
            operation=op_name).execute()['status']
    print(f'[{int(t/60)}m {t%60}s] '
          f'Deployment operation finished. Status: {op_status}')


def list_deployments():
    # Get current credentials from environment variables and build deployment API object
    credentials, project_id = google.auth.default()
    deployment_api = discovery.build(
        'deploymentmanager', 'v2', credentials=credentials)
    # Get list of deployments
    try:
        deployments_list = deployment_api.deployments().list(
            project=project_id).execute()['deployments']
    except KeyError:
        return []
    deployed_level_names = []
    for deployment in deployments_list:
        deployed_level_names.append(deployment['name'])
    return deployed_level_names
