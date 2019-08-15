import os

from google.cloud import storage


def upload_directory_recursive(top_dir_path, bucket):
    for dir_path, subdir_paths, f_names in os.walk(top_dir_path):
        for f in f_names:
            abs_path = dir_path + '/' + f
            rel_path = abs_path.replace(top_dir_path+'/', '')
            #abs_path = top_dir_path + '/' + relative_path
            blob = storage.Blob(rel_path, bucket)
            with open(abs_path, 'rb') as f:
                blob.upload_from_file(f)


def delete_bucket(bucket_name):
    # Forcefully delete bucket to also get rid of items inside bucket
    storage_client = storage.Client()
    bucket = storage_client.lookup_bucket(bucket_name)
    if bucket:
        bucket.delete(force=True)
