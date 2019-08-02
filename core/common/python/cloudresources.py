import os

from google.cloud import storage
import google.auth
import googleapiclient.discovery


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


def delete_bucket(bucket_name):
    # Forcefully delete bucket to also get rid of items inside bucket
    storage_client = storage.Client()
    bucket = storage_client.lookup_bucket(bucket_name)
    if bucket:
        bucket.delete(force=True)


def remove_accounts_iam(accounts):
    credentials, project_id = google.auth.default()
    crm_api = googleapiclient.discovery.build(
        'cloudresourcemanager', 'v1', credentials=credentials)
    # Get current iam policy
    policy = crm_api.projects().getIamPolicy(
        resource=project_id, body={}).execute()

    # Remove given accounts from policy
    for binding in policy['bindings']:
        binding['members'] = (
            [member for member in binding['members']
             if not member in [f'serviceAccount:{account}@{project_id}.iam.gserviceaccount.com' for account in accounts]])

    # Set as new policy
    crm_api.projects().setIamPolicy(resource=project_id,
                                    body={'policy': policy}).execute()
