import os
from google.cloud import storage

XOR_FACTOR = {{ xor_factor }}


def main(request):
    # Exit if request does not include password
    if not 'password' in request.args:
        return 'Must include \"password\" argument in request\n'
    try:
        password = int(request.args.get('password'))
    except ValueError:
        return 'Password must be an integer\n'

    XOR_PASSWORD = int(os.environ.get('XOR_PASSWORD'))

    # Exit if password is not correct
    if not password ^ XOR_FACTOR == XOR_PASSWORD:
        return 'Password yielded incorrect result\n'

    # Read and return secret
    bucket_name = '{{ bucket_name }}'
    storage_client = storage.Client()
    bucket = storage_client.get_bucket(bucket_name)
    secret_blob = storage.Blob('secret.txt', bucket)
    return f'Correct password. The secret is: {secret_blob.download_as_string().decode("utf-8")}\n'
