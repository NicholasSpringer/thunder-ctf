from flask import render_template
def main(request):
	from googleapiclient import discovery
	import google.auth
	import os
	
	
	# Set the project ID
	PROJECT_ID = os.environ['GCP_PROJECT']
	
	# Get function env variable
	NONCE = os.environ.get('NONCE', 'Specified environment variable is not set.')
	RESOURCE_PREFIX = os.environ.get('RESOURCE_PREFIX', 'Specified environment variable is not set.')
	LEVEL_NAME = os.environ.get('LEVEL_NAME', 'Specified environment variable is not set.')

	PRI = {{fvar|safe}}[0]
	
	# Get credential of cloud function account
	credentials, project_id = google.auth.default()

	# Build cloudresourcemanager REST API python object
	service_r = discovery.build('cloudresourcemanager','v1', credentials=credentials)
	
	# Service account 
	sa = f'serviceAccount:{RESOURCE_PREFIX}-f-access-{NONCE}-sa@{PROJECT_ID}.iam.gserviceaccount.com'

	get_iam_policy_request_body = {}
	
	roles =[]
	permissions =[]
	msg = ''
	err=''
	try:
		bindings = service_r.projects().getIamPolicy(resource=PROJECT_ID, body=get_iam_policy_request_body).execute()["bindings"]
		for r in bindings:
			if sa in r["members"]:
				roles.append(r["role"])
	except Exception as e: 
		permissions =[]
		msg ='There is an error'
		err = str(e)
	if len(roles)>1 or PRI != roles[0]:
		msg='Not least privilege role, please try again!'
	else:
		msg='Congratulations! You got the least privilege role.'
		
		
	# Build iam  REST API python object
	service_i = discovery.build('iam','v1', credentials=credentials)

	
	try:
		permissions = service_i.roles().get(name=roles[0]).execute()["includedPermissions"]
		
		
	except Exception as e: 
		permission =[]
		err = str(e)
	
	return render_template(f'{RESOURCE_PREFIX}-check.html',  pers=permissions, msg=msg, rn=roles[0], err=err, prefix=RESOURCE_PREFIX,level_name=LEVEL_NAME,nonce=NONCE)