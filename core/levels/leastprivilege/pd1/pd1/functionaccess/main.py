from flask import render_template
def main(request):
	from googleapiclient import discovery
	import google.auth
	import os

	
	# Set the project ID
	PROJECT_ID = os.environ['GCP_PROJECT']
	FUNCTION_REGION = os.environ['FUNCTION_REGION']
	NONCE = os.environ.get('NONCE', 'Specified environment variable is not set.')
	RESOURCE_PREFIX = os.environ.get('RESOURCE_PREFIX', 'Specified environment variable is not set.')
	LEVEL_NAME = os.environ.get('LEVEL_NAME', 'Specified environment variable is not set.')

	# Get credential of cloud function account
	credentials, project_id = google.auth.default()


	#Build storage REST API python object
	storage_api = discovery.build('storage', 'v1', credentials=credentials,cache_discovery=False)
	name = f'{RESOURCE_PREFIX}-bucket-{NONCE}'
	err=[]
	resources = []
	try:
		request = storage_api.objects().list(bucket=name).execute()["items"][0]
		bucket = name + ' :  ' + request["name"]
		resources.append(bucket)

	except Exception as e:
		resources.append('Insufficient privilege!') 
		err.append(str(e))
	
	url=f'https://{FUNCTION_REGION}-{PROJECT_ID}.cloudfunctions.net/{RESOURCE_PREFIX}-f-check-{NONCE}'
	
	
	return render_template(f'{RESOURCE_PREFIX}-access.html', resources=resources, url=url, err=err,prefix=RESOURCE_PREFIX,level_name=LEVEL_NAME, nonce=NONCE)

	

