from flask import render_template
def main(request):
	import google.auth
	from google.cloud import datastore
	import os
	
	
	# Set the project ID
	PROJECT_ID = os.environ['GCP_PROJECT']
	FUNCTION_REGION = os.environ['FUNCTION_REGION']
	NONCE = os.environ.get('NONCE', 'Specified environment variable is not set.')
	RESOURCE_PREFIX = os.environ.get('RESOURCE_PREFIX', 'Specified environment variable is not set.')
	LEVEL_NAME = os.environ.get('LEVEL_NAME', 'Specified environment variable is not set.')

	# Get credential of cloud function account
	credentials, project_id = google.auth.default()

	#score function url
	surl  = f'https://{FUNCTION_REGION}-{PROJECT_ID}.cloudfunctions.net/scores-f-{NONCE}'

	#Build datastore REST API python object
	client = datastore.Client(credentials=credentials )
	err=[]
	resources = []
	try:
		kind=f'{RESOURCE_PREFIX}-{NONCE}-{PROJECT_ID}'
		query = client.query(kind=kind)
		for q in list(query.fetch()):
			resources.append({'kind':kind,'name': q['name'],'password': q['password'],'active': q['active']})

	except Exception as e:
		resources.append('Insufficient privilege!') 
		err.append(str(e))
	
	url=f'https://{FUNCTION_REGION}-{PROJECT_ID}.cloudfunctions.net/{RESOURCE_PREFIX}-f-check-{NONCE}'
	
	
	return render_template(f'{RESOURCE_PREFIX}-access.html', resources=resources, url=url, err=err,prefix=RESOURCE_PREFIX, level_name=LEVEL_NAME, nonce=NONCE,surl=surl)

	

