import json
import base64

from cryptography.hazmat.primitives import serialization as crypto_serialization
from cryptography.hazmat.primitives.asymmetric import rsa
from cryptography.hazmat.backends import default_backend as crypto_default_backend

def generate_ssh_keypair():
    '''Returns a random RSA public/private keypair that can be used for SSH

    Returns:
        tuple: private_key, public_key
        - private_key (str) - The private key of the keypair
        - public_key (str) - The public key of the keypair
    '''
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
    public_key = public_key.decode('utf-8')
    return private_key, public_key
