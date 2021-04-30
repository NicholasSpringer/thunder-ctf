import requests
from googleapiclient import discovery
import google.auth
import csv
import requests

users = csv.DictReader(open('/home/ajn6/thunder-ctf/core/levels/defender/audit/resources/devs.csv', newline=''))
credentials, project_id = google.auth.default()
service = discovery.build('compute', 'v1', credentials=credentials)
response = service.instances().list(project=project_id, zone='us-west1-b').execute()

for instance in response['items']:
    if instance['name'] == 'api-engine':
        hostname = instance['networkInterfaces'][0]['accessConfigs'][0]['natIP']
        break

print(hostname)
url = "http://" + hostname
print(url)
for user in users:
    r = requests.post(url, data=user)
    print(r.text)

follow_url = url + '/follow'
print(follow_url)
r = requests.post(follow_url, data={'follower': 1, 'followee': 2})
print(r.text)
