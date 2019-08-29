import os

from google.cloud import storage


def upload_directory_recursive(top_dir_path, bucket_name):
    '''Recursively uploads all the files in the given directory path to the bucket with the given name.

    Parameters:
        top_dir_path (str): Relative path to the directory that will be uploaded, starting with "core/"
        bucket_name (str): Name of the GCS bucket.
    '''
    # Get bucket object
    storage_client = storage.Client()
    bucket = storage_client.get_bucket(bucket_name)
    # Recursively go through the subfiles and subdirectories of the directory and upload the files
    for dir_path, subdir_paths, f_names in os.walk(top_dir_path):
        for f in f_names:
            abs_path = dir_path + '/' + f
            rel_path = abs_path.replace(top_dir_path+'/', '')
            blob = storage.Blob(rel_path, bucket)
            with open(abs_path, 'rb') as f:
                blob.upload_from_file(f)


def delete_bucket(bucket_name):
    '''Deletes the bucket of the given name if it exists, even if there are objects in the bucket.'''
    # Forcefully delete bucket to also get rid of items inside bucket
    storage_client = storage.Client()
    bucket = storage_client.lookup_bucket(bucket_name)
    if bucket:
        bucket.delete(force=True)
