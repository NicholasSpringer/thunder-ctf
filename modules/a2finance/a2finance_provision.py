import os
import subprocess
import shutil
import random
import json
from git import Repo
from google.cloud import storage, logging_v2
from google.auth import default
from google.cloud.logging_v2.resource import Resource
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import rsa
from cryptography.hazmat.backends import default_backend

START_DIR = "start"
INSTRUCTIONS_DIR = "instructions"
FIRST_NAMES_PATH = "modules/a2finance/first-names.txt"
LAST_NAMES_PATH = "modules/a2finance/last-names.txt"
ZONE = "us-central1-a"
VM_NAME = "a2-logging-instance"
SSH_USERNAME = "clouduser"

def load_names():
    with open(FIRST_NAMES_PATH) as f:
        first_names = [name.strip().title() for name in f if name.strip()]
    with open(LAST_NAMES_PATH) as f:
        last_names = [name.strip().title() for name in f if name.strip()]
    return first_names, last_names

def generate_ssh_keypair(private_path, public_path):
    key = rsa.generate_private_key(
        backend=default_backend(), public_exponent=65537, key_size=2048
    )
    private_key = key.private_bytes(
        serialization.Encoding.PEM,
        serialization.PrivateFormat.PKCS8,
        serialization.NoEncryption(),
    )
    public_key = key.public_key().public_bytes(
        serialization.Encoding.OpenSSH, serialization.PublicFormat.OpenSSH
    )
    if os.path.exists(private_path):
        os.remove(private_path)
    with open(private_path, "wb") as f:
        f.write(private_key)
    with open(public_path, "wb") as f:
        f.write(public_key)

def create_git_repo(leak_key_path):
    repo_dir = "/tmp/a2-gitrepo"
    if os.path.exists(repo_dir):
        shutil.rmtree(repo_dir)
    os.makedirs(repo_dir)

    # Add dummy source code
    with open(os.path.join(repo_dir, "main.py"), "w") as f:
        f.write("print('hello')\n")

    # Add leaked SSH key
    shutil.copy(leak_key_path, os.path.join(repo_dir, "ssh_key"))

    # Initialize Git repo
    repo = Repo.init(repo_dir)
    repo.git.config("user.email", "johndoe@example.com")
    repo.git.config("user.name", "John Doe")
    repo.git.add(A=True)
    repo.index.commit("added initial files")

    # Remove key and commit again
    os.remove(os.path.join(repo_dir, "ssh_key"))
    repo.git.add(A=True)
    repo.index.commit("Oops. Deleted accidental key upload")

    return repo_dir

def upload_to_gcs(bucket_name, source_dir):
    client = storage.Client()
    bucket = client.bucket(bucket_name)
    for root, _, files in os.walk(source_dir):
        for file in files:
            full_path = os.path.join(root, file)
            rel_path = os.path.relpath(full_path, source_dir)
            blob = bucket.blob(rel_path)
            blob.upload_from_filename(full_path)

def write_log_entry(target_name):
    credentials, project_id = default()
    log_client = logging_v2.Client()
    logger = log_client.logger("transactions")

    logger.log_struct(
        {
            "name": target_name,
            "card": f"{random.randint(1000,9999)}-{random.randint(1000,9999)}-{random.randint(1000,9999)}-{random.randint(1000,9999)}",
            "amount": f"{random.randint(10, 999)}.00",
        },
        resource=Resource(type="global", labels={})
    )

def write_log_entries(target_name, count=100):
    credentials, project_id = default()
    log_client = logging_v2.Client()
    logger = log_client.logger("transactions")
    first_names, last_names = load_names()

    # Randomly choose which log will contain the target name
    target_index = random.randint(0, count - 1)

    for i in range(count):
        if i == target_index:
            name = target_name
        else:
            name = f"{random.choice(first_names)} {random.choice(last_names)}"

        logger.log_struct(
            {
                "name": name,
                "card": f"{random.randint(1000,9999)}-{random.randint(1000,9999)}-{random.randint(1000,9999)}-{random.randint(1000,9999)}",
                "amount": f"{random.randint(10, 999)}.00",
            },
            resource=Resource(type="global", labels={})
        )

def get_bucket_from_file():
    with open("start/a2_bucket_name.txt") as f:
        return f.read().strip()

def inject_ssh_key(project_id, zone, instance_name, ssh_username, pubkey_path):
    with open(pubkey_path, "r") as f:
        pubkey = f.read().strip()
    ssh_metadata = f"{ssh_username}:{pubkey}"
    subprocess.run([
        "gcloud", "compute", "instances", "add-metadata", instance_name,
        "--metadata", f"ssh-keys={ssh_metadata}",
        "--zone", zone,
        "--project", project_id
    ], check=True)

def write_start_info(target_name):
    os.makedirs(START_DIR, exist_ok=True)
    os.makedirs(INSTRUCTIONS_DIR, exist_ok=True)
    instruction = (
        f"Use the compromised service account credentials stored in start/a2-access.json to find the credit card number of {target_name}, "Add commentMore actions
        "which is hidden somewhere in the GCP project."
    )
    with open(os.path.join("instructions", "a2finance.txt"), "w") as f:
        f.write(instruction + "\n")

def main():
    os.makedirs(START_DIR, exist_ok=True)
    priv_path = os.path.join(START_DIR, "a2_key")
    pub_path = priv_path + ".pub"

    generate_ssh_keypair(priv_path, pub_path)
    os.chmod(priv_path, 0o400)

    repo_dir = create_git_repo(priv_path)
    bucket = get_bucket_from_file()
    upload_to_gcs(bucket, repo_dir)

    first_names, last_names = load_names()
    target_name = f"{random.choice(first_names)} {random.choice(last_names)}"
    write_log_entries(target_name, count=100)
    write_start_info(target_name)

    # Inject SSH public key into VM
    project_id = os.popen("gcloud config get-value project").read().strip()
    inject_ssh_key(project_id, ZONE, VM_NAME, SSH_USERNAME, pub_path)

if __name__ == "__main__":
    main()
