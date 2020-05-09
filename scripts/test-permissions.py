from googleapiclient import discovery
import google.oauth2.service_account
from google.oauth2.credentials import Credentials
import os, sys
from permissions import permissions

if len(sys.argv) != 2:
    sys.exit("Usage python test-permissions <token | path_to_key_file>")

if os.getenv('GOOGLE_CLOUD_PROJECT'):
    PROJECT_ID = os.getenv('GOOGLE_CLOUD_PROJECT')
    print(PROJECT_ID)
else:
    sys.exit("Please set your GOOGLE_CLOUD_PROJECT environment variable via gcloud config set project [PROJECT_ID]")

if (os.path.exists(sys.argv[1])):
    print(f'JSON credential: {sys.argv[1]}')
    # Create credentials using service account key file
    credentials = google.oauth2.service_account.Credentials.from_service_account_file(sys.argv[1])
else:
    print(f'Access token: {sys.argv[1][0:4]}...{sys.argv[1][-4:]}')
    ACCESS_TOKEN = sys.argv[1]
    # Create credentials using access token
    credentials = Credentials(token=sys.argv[1])

# Change current working directory to top level of repo
os.chdir(os.path.dirname(os.getcwd()+'/'+os.path.dirname(__file__)))
# Load testable permissions into list
#with open('scripts/testable-permissions.txt') as f:
    #testable_permissions = f.read().split('\n')
# Split testable permissions list into lists of 100 items each
chunked_permissions = (
    [permissions[i * 100:(i + 1) * 100] for i in range((len(permissions)+99) // 100)])

# Build cloudresourcemanager REST API python object
crm_api = discovery.build('cloudresourcemanager',
                          'v1', credentials=credentials)

# For each list of 100 permissions, query the api to see if the service account has any of the permissions
given_permissions = []
for permissions_chunk in chunked_permissions:
    response = crm_api.projects().testIamPermissions(resource=PROJECT_ID, body={
        'permissions': permissions_chunk}).execute()
    # If the service account has any of the permissions, add them to the output list
    if 'permissions' in response:
        given_permissions.extend(response['permissions'])

print(given_permissions)
