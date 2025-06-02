import os
import json
import random
import base64

from google.cloud import storage
from googleapiclient.discovery import build
from google.oauth2 import service_account
import google.auth

MODULE_DIR = os.path.dirname(__file__)
START_DIR = os.path.abspath(os.path.join(MODULE_DIR, "../../start"))
GENERATED_DIR = os.path.join(MODULE_DIR, "generated")

os.makedirs(START_DIR, exist_ok=True)

# Read bucket names
with open(os.path.join(GENERATED_DIR, "bucket1.txt")) as f:
    bucket1_name = f.read().strip()
with open(os.path.join(GENERATED_DIR, "bucket2.txt")) as f:
    bucket2_name = f.read().strip()

# Get current credentials and project ID
credentials, project_id = google.auth.default()

# Create a service account key via API (not Terraform)
sa_email = f"audit-npc@{project_id}.iam.gserviceaccount.com"
iam = build("iam", "v1", credentials=credentials)
key = iam.projects().serviceAccounts().keys().create(
    name=f"projects/{project_id}/serviceAccounts/{sa_email}", body={}
).execute()

key_data = base64.b64decode(key["privateKeyData"]).decode("utf-8")
key_path = os.path.join(START_DIR, "audit-npc.json")
with open(key_path, "w") as f:
    f.write(key_data)

# Upload dummy data
storage_client = storage.Client()
index = 0
for bucket_name in [bucket1_name, bucket2_name]:
    bucket = storage_client.bucket(bucket_name)
    for _ in range(6):
        blob = bucket.blob(f"data{index}.txt")
        blob.upload_from_string(str(random.randint(100000000000, 999999999999)))
        index += 1

# Use leaked key to simulate access
leaked_creds = service_account.Credentials.from_service_account_file(key_path)
leaked_client = storage.Client(credentials=leaked_creds)
bucket = leaked_client.get_bucket(bucket1_name)

secret_index = random.randrange(0, index - 1, 2)
blob = bucket.blob(f"data{secret_index}.txt")
_ = blob.exists()  # Triggers storage.buckets.get in audit logs

# Save secret blob name
with open(os.path.join(START_DIR, "audit_secret.txt"), "w") as f:
    f.write(blob.name + "\n")
