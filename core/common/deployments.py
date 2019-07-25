import random
import os
import time

from google.cloud import storage
import google.auth
import googleapiclient.discovery


def read_config(file_name, config_properties={}):
    with open(file_name) as f:
        content = f.read()
    for key in config_properties.keys():
        content = content.replace('//'+key+'//', config_properties[key])
    return content


def insert(level_name, config_file, template_files=[],
           config_properties={}, labels={}):
    # Get current credentials from environment variables and build deployment API object
    credentials, project_id = google.auth.default()
    deployment_api = googleapiclient.discovery.build(
        'deploymentmanager', 'v2', credentials=credentials)

    level_directory = 'core/levels/'+level_name+'/'
    # Create request to insert deployment
    request_body = {
        "name": level_name,
        "target": {
            "config": {
                "content": read_config(
                    level_directory + config_file,
                    config_properties=config_properties)
            },
            "imports": []
        },
        "labels": []
    }
    # Add imports to deployment json
    for template in template_files:
        request_body['target']['imports'].append({
            "name": os.path.basename(template),
            "content": read_config(level_directory + template)
        })
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


def delete(level_name):
    # Get current credentials from environment variables and build deployment API object
    credentials, project_id = google.auth.default()
    deployment_api = googleapiclient.discovery.build(
        'deploymentmanager', 'v2', credentials=credentials)
    # Send delete request
    op_name = deployment_api.deployments().delete(
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
    deployment_api = googleapiclient.discovery.build(
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
    deployment_api = googleapiclient.discovery.build(
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

def upload_directory_recursive(dir_path, top_dir, bucket):
    for subitem in os.listdir(dir_path):
        subitem_path = dir_path + "/" + subitem
        if os.path.isdir(subitem_path):
            upload_directory_recursive(subitem_path, top_dir, bucket)
        else:
            relative_file_path = subitem_path.replace(top_dir + '/', '', 1)
            blob = storage.Blob(relative_file_path, bucket)
            with open(subitem_path, 'rb') as f:
                blob.upload_from_file(f)

def clear_bucket():
    pass