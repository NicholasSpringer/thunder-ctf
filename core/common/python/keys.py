import os
import json
import base64

from cryptography.hazmat.primitives import serialization as crypto_serialization
from cryptography.hazmat.primitives.asymmetric import rsa
from cryptography.hazmat.backends import default_backend as crypto_default_backend

import google.auth
import googleapiclient.discovery


def generate_ssh_key():
    # Generate private key
    key = rsa.generate_private_key(
        backend=crypto_default_backend(),
        public_exponent=65537,
        key_size=2048
    )
    # Export private and public key as strings
    private_key = key.private_bytes(
        crypto_serialization.Encoding.PEM,
        crypto_serialization.PrivateFormat.PKCS8,
        crypto_serialization.NoEncryption()).decode('utf-8')
    public_key = key.public_key().public_bytes(
        crypto_serialization.Encoding.OpenSSH,
        crypto_serialization.PublicFormat.OpenSSH)
    # Add username to public key
    public_key = public_key.decode('utf-8')

    return private_key, public_key


def generate_service_account_key(service_account_id):
    # Get current credentials from environment variables and build deployment API object
    credentials, project_id = google.auth.default()
    service_account_email = f'{service_account_id}@{project_id}.iam.gserviceaccount.com'
    iam_api = googleapiclient.discovery.build(
        'iam', 'v1', credentials=credentials)
    # Create new key
    key = iam_api.projects().serviceAccounts().keys().create(
        name=f'projects/{project_id}/serviceAccounts/{service_account_email}', body={}).execute()
    # Get service account ID
    unique_id = iam_api.projects().serviceAccounts().get(
        name=f'projects/{project_id}/serviceAccounts/{service_account_email}').execute['uniqueId']
    # Assemble object in key file format
    key_file_content = base64.b64decode(key['privateKeyData']).decode('unicode-escape')
    # Return json string
    return key_file_content
