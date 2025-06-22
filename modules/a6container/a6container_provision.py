import os
import base64
import google.auth
from google.cloud import storage
from googleapiclient import discovery

SERVICE_ACCOUNT_ID = "a6-access"
KEY_FILENAME = f"{SERVICE_ACCOUNT_ID}.json"

base_dir = os.path.dirname(__file__)
start_dir = os.path.abspath(os.path.join(base_dir, "../../start"))
generated_dir = os.path.join(base_dir, "generated")
bucket_file = os.path.join(generated_dir, "bucket_name.txt")

def upload_secret(bucket_name: str):
    client = storage.Client()
    bucket = client.bucket(bucket_name)
    blob = bucket.blob("secret.txt")
    blob.upload_from_string("ThunderCTF{container_escape_possible_here}\n")
    print(f"[UPLOAD] secret.txt -> gs://{bucket_name}/secret.txt")

def generate_service_account_key(service_account_id: str) -> str:
    credentials, project_id = google.auth.default()
    service_account_email = f"{service_account_id}@{project_id}.iam.gserviceaccount.com"
    iam_api = discovery.build('iam', 'v1', credentials=credentials)

    key = iam_api.projects().serviceAccounts().keys().create(
        name=f'projects/{project_id}/serviceAccounts/{service_account_email}',
        body={}
    ).execute()

    return key["privateKeyData"]

def write_start_file(message: str, key_data: str):
    instructions_dir = os.path.abspath(os.path.join(base_dir, "../../instructions"))
    os.makedirs(start_dir, exist_ok=True)
    os.makedirs(instructions_dir, exist_ok=True)

    # Write instructions to instructions/a6container.txt
    with open(os.path.join(instructions_dir, "a6container.txt"), "w") as f:
        f.write(message + "\n")
    os.chmod(os.path.join(instructions_dir, "a6container.txt"), 0o400)

    # Write service account key to start/a6-access.json
    with open(os.path.join(start_dir, KEY_FILENAME), "w") as f:
        f.write(base64.b64decode(key_data).decode("utf-8"))
    os.chmod(os.path.join(start_dir, KEY_FILENAME), 0o400)

def main():
    with open(bucket_file) as f:
        bucket_name = f.read().strip()

    upload_secret(bucket_name)

    key_data = generate_service_account_key(SERVICE_ACCOUNT_ID)

    instructions = (
        "Use the compromised service account credentials given to you to find the secret, "
        "which is located in a file called secret.txt in a private bucket on the project."
    )

    write_start_file(instructions, key_data)

if __name__ == "__main__":
    main()
