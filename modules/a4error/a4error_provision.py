
import os
import google.auth
from google.cloud import storage
from googleapiclient import discovery
import base64
import zipfile
import time

ZONE = "us-west1-b"
INSTANCE_NAME = "a4-instance"
SERVICE_ACCOUNT_ID = "a4-access"
KEY_FILENAME = f"{SERVICE_ACCOUNT_ID}.json"

base_dir = os.path.dirname(__file__)
start_dir = os.path.abspath(os.path.join(base_dir, "../../start"))
generated_dir = os.path.join(base_dir, "generated")
bucket_file = os.path.join(generated_dir, "bucket_name.txt")
instructions_dir = os.path.abspath(os.path.join(base_dir, "../../instructions"))
bucket_dir = os.path.join(base_dir, "bucket")
function_dir = os.path.join(base_dir, "function")
function_zip_path = os.path.join(base_dir, "function.zip")
os.makedirs(instructions_dir, exist_ok=True)

def generate_service_account_key(service_account_id: str) -> str:
    credentials, project_id = google.auth.default()
    service_account_email = f"{service_account_id}@{project_id}.iam.gserviceaccount.com"
    iam_api = discovery.build('iam', 'v1', credentials=credentials)

    key = iam_api.projects().serviceAccounts().keys().create(
        name=f'projects/{project_id}/serviceAccounts/{service_account_email}',
        body={}
    ).execute()

    return key["privateKeyData"]

def write_start_file(key_data: str):
    os.makedirs(start_dir, exist_ok=True)
    os.makedirs(instructions_dir, exist_ok=True)

    # Hardcoded instruction for a4error
    instruction = (
        'In this level, look for a file named "secret.txt," which is owned by "secretuser." '
        "Use the given compromised credentials to find it."
    )

    with open(os.path.join(instructions_dir, "a4error.txt"), "w") as f:
        f.write(instruction + "\n")

    with open(os.path.join(start_dir, KEY_FILENAME), "w") as f:
        f.write(base64.b64decode(key_data).decode("utf-8"))



def upload_dummy_files(bucket_name: str):
    storage_client = storage.Client()
    bucket = storage_client.bucket(bucket_name)

    for dirpath, _, filenames in os.walk(bucket_dir):
        for fname in filenames:
            full_path = os.path.join(dirpath, fname)
            rel_path = os.path.relpath(full_path, bucket_dir)
            blob = bucket.blob(rel_path)
            blob.upload_from_filename(full_path)
            print(f"[UPLOAD] {rel_path} -> gs://{bucket_name}")

def clear_instance_metadata(instance_name: str, zone: str):
    credentials, project_id = google.auth.default()
    compute_api = discovery.build("compute", "v1", credentials=credentials)

    instance_info = compute_api.instances().get(
        project=project_id, zone=zone, instance=instance_name
    ).execute()
    fingerprint = instance_info["metadata"]["fingerprint"]

    compute_api.instances().setMetadata(
        project=project_id,
        zone=zone,
        instance=instance_name,
        body={"fingerprint": fingerprint, "items": []},
    ).execute()

def create_function_zip(bucket_name: str):
    os.makedirs(function_dir, exist_ok=True)

    main_py_code = f'''
import requests

BUCKET_NAME = "{bucket_name}"

def main(request):
    if 'file' not in request.args:
        return ('Querying REST API to access bucket: gs://' + BUCKET_NAME + '\\n'
                'To read a specific file include "file" argument: ?file=[filename]\\n')
    else:
        # Caller token (debug)
        print("Caller Authorization Header:", request.headers.get("Authorization"))

        # Internal metadata-based token
        token = requests.get(
            'http://metadata.google.internal/computeMetadata/v1/instance/service-accounts/default/token',
            headers={{'Metadata-Flavor': 'Google'}}).json()['access_token']

        obj_path = request.args["file"]
        gcs_req = requests.Request(
            'GET',
            f'https://www.googleapis.com/storage/v1/b/{{BUCKET_NAME}}/o/{{obj_path}}?alt=media',
            headers={{'Authorization': f'Bearer {{token}}'}}).prepare()

        response = requests.Session().send(gcs_req)
        try:
            response.raise_for_status()
        except requests.exceptions.HTTPError:
            raise requests.exceptions.HTTPError(f"Request failed.\\n Request:\\n{{request_string(gcs_req)}}")
        return response.text + '\\n'

def request_string(req):
    return (f'{{req.method}} {{req.url}}\\n\\n' +
            '\\n'.join(f'{{k}}: {{v}}' for k, v in req.headers.items()) +
            (('\\n\\n' + req.body) if req.body else ''))
'''

    main_py_code = main_py_code.replace("{{", "{").replace("}}", "}")

    main_py_path = os.path.join(function_dir, "main.py")
    with open(main_py_path, "w") as f:
        f.write(main_py_code.strip())

    # Write requirements.txt
    requirements_path = os.path.join(function_dir, "requirements.txt")
    with open(requirements_path, "w") as f:
        f.write("requests\n")

    # Create function.zip
    with zipfile.ZipFile(function_zip_path, "w") as zipf:
        zipf.write(main_py_path, arcname="main.py")
        zipf.write(requirements_path, arcname="requirements.txt")

def wait_for_file(path, timeout=10):
    waited = 0
    while not os.path.exists(path) and waited < timeout:
        time.sleep(1)
        waited += 1
    if not os.path.exists(path):
        raise FileNotFoundError(f"{path} not found after waiting {timeout} seconds")

def cleanup():
    for path in [function_dir, generated_dir, function_zip_path]:
        if os.path.exists(path):
            if os.path.isdir(path):
                os.system(f"rm -rf {path}")
            else:
                os.remove(path)


def main():
    wait_for_file(bucket_file)
    with open(bucket_file) as f:
        bucket_name = f.read().strip()

    upload_dummy_files(bucket_name)
    create_function_zip(bucket_name)
    time.sleep(180)  # wait 180 seconds before clearing metadata
    clear_instance_metadata(INSTANCE_NAME, ZONE)
    key_data = generate_service_account_key(SERVICE_ACCOUNT_ID)
    write_start_file(key_data)


if __name__ == "__main__":
    main()
