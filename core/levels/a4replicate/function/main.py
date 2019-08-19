import requests
BUCKET_NAME = '{{ bucket_name }}'


def main(request):
    # If the user did not
    if not 'file' in request.args:
        return ('Querying REST API to access bucket: gs://{{ bucket_name }}. File list:\n'
                '- file1.txt\n'
                '- file2.txt\n'
                'To read a file include "file" argument: ?file=[filename]\n')
    else:
        token = requests.get('http://metadata.google.internal/computeMetadata/v1/instance/service-accounts/default/token',
                             headers={'Metadata-Flavor': 'Google'}).json()['access_token']
        obj_path = request.args["file"]
        gcs_req = requests.Request(
            'GET',
            f'https://www.googleapis.com/storage/v1/b/{BUCKET_NAME}/o/{obj_path}?alt=media',
            headers={'Authorization': f'Bearer {token}'}).prepare()
        response = requests.Session().send(gcs_req)
        try:
            response.raise_for_status()
        except requests.exceptions.HTTPError:
            raise requests.exceptions.HTTPError(
                f"Request failed.\n Request:\n{request_string(gcs_req)}")
        return response.text + '\n'


def request_string(req):
    return (f'{req.method} {req.url}\n\n' +
            '\n'.join(f'{k}: {v}' for k, v in req.headers.items()) +
            (('\n\n' + req.body) if req.body else ''))
