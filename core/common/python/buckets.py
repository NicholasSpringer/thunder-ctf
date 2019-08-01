import os
from google.cloud import storage

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