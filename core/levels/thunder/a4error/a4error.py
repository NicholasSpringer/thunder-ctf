import os
import google.auth
from google.cloud import storage
from googleapiclient import discovery
from core.framework import levels, iam

LEVEL_PATH = 'thunder/a4error'
RESOURCE_PREFIX = 'a4'

# These must match Terraform values
BUCKET_NAME_FILE = 'start/a4_bucket_name.txt'
INSTANCE_NAME = 'a4-instance'
ZONE = 'us-west1-b'
KEY_FILENAME = 'a4-access.json'

def main():
    print(f"[INFO] Running provision logic for {LEVEL_PATH}")

    # Load credentials and project ID
    credentials, project_id = google.auth.default()

    # Read bucket name from Terraform-provided file
    with open(BUCKET_NAME_FILE, 'r') as f:
        bucket_name = f.read().strip()

    print(f"[INFO] Target GCS bucket: {bucket_name}")

    # Upload core/levels/thunder/a4error/bucket/* to GCS bucket
    storage_client = storage.Client()
    bucket = storage_client.bucket(bucket_name)
    local_path = f'core/levels/{LEVEL_PATH}/bucket'
    for dirpath, _, filenames in os.walk(local_path):
        for fname in filenames:
            rel_path = os.path.relpath(os.path.join(dirpath, fname), local_path)
            blob = bucket.blob(rel_path)
            blob.upload_from_filename(os.path.join(dirpath, fname))
            print(f"[UPLOAD] {rel_path} uploaded to {bucket_name}")

    # Clear startup script from VM metadata
    compute = discovery.build('compute', 'v1', credentials=credentials)
    instance_info = compute.instances().get(
        project=project_id, zone=ZONE, instance=INSTANCE_NAME).execute()
    fingerprint = instance_info['metadata']['fingerprint']
    compute.instances().setMetadata(
        project=project_id,
        zone=ZONE,
        instance=INSTANCE_NAME,
        body={'fingerprint': fingerprint, 'items': []}
    ).execute()
    print(f"[INFO] Cleared VM metadata from {INSTANCE_NAME}")

    # Generate service account key
    sa_key = iam.generate_service_account_key(f'{RESOURCE_PREFIX}-access')
    levels.write_start_info(
        LEVEL_PATH,
        'In this level, look for a file named "secret.txt," which is owned by "secretuser." Use the given compromised credentials to find it.',
        file_name=KEY_FILENAME,
        file_content=sa_key
    )
    print(f"[KEY] Service account key written to start/{KEY_FILENAME}")
    print("[DONE] a4error provision complete.")

if __name__ == "__main__":
    main()
