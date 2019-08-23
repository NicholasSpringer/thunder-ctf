import os
import shutil
import zipfile
import httplib2
import jinja2

import google.auth
from googleapiclient import discovery

def upload_cloud_function(function_path, location_id, template_args={}):
    temp_func_path = function_path + '-temp'
    zip_path = os.path.dirname(temp_func_path) + '/' + 'function.zip'
    try:
        create_temp_cf_files(function_path, temp_func_path,
                             template_args=template_args)
        credentials, project_id = google.auth.default()
        # Create zip
        with zipfile.ZipFile(zip_path, 'w') as z:
            for dir_path, subdir_paths, f_names in os.walk(temp_func_path):
                for f in f_names:
                    file_path = dir_path + '/' + f
                    arc_path = file_path.replace(temp_func_path+'/', '')
                    z.write(file_path, arcname=arc_path)
        # Build api object
        cf_api = discovery.build('cloudfunctions',
                                 'v1', credentials=credentials)
        parent = f'projects/{project_id}/locations/{location_id}'
        # Generate upload URL
        upload_url = cf_api.projects().locations().functions(
        ).generateUploadUrl(parent=parent).execute()['uploadUrl']
        # Make Http object
        h = httplib2.Http()
        # Upload to url
        headers = {'Content-Type': 'application/zip',
                   'x-goog-content-length-range': '0,104857600'}
        with open(zip_path, 'rb') as f:
            h.request(upload_url, method='PUT', headers=headers, body=f)
        # Return signed url for creating cloud function
        return upload_url
    finally:
        # Delete zip
        if os.path.exists(zip_path):
            os.remove(zip_path)
        # Delete temp file
        if os.path.exists(temp_func_path):
            shutil.rmtree(temp_func_path)


def create_temp_cf_files(func_path, temp_func_path, template_args={}):
    # Iterate recursively through all subfiles
    for dir_path, subdir_paths, f_names in os.walk(func_path):
        for f in f_names:
            file_path = dir_path + '/' + f
            temp_path = file_path.replace(func_path, temp_func_path)
            # Read and render function template
            with open(file_path) as f:
                rendered_template = jinja2.Template(
                    f.read()).render(**template_args)
            # If temporary path doesn't exist yet, create the directory structure
            if not os.path.exists(os.path.dirname(temp_path)):
                os.makedirs(os.path.dirname(temp_path))
            # Write to temporary file
            with open(temp_path, 'w+') as f:
                f.write(rendered_template)
