from flask import render_template
def main(request):
	from googleapiclient import discovery
	import google.oauth2.service_account
	from google.oauth2.credentials import Credentials
	import os
	from cryptography.fernet import Fernet

	
	# Set the project ID
	PROJECT_ID = os.environ['GCP_PROJECT']
	
	# Get function env variable
	NONCE = os.environ.get('NONCE', 'Specified environment variable is not set.')
	RESOURCE_PREFIX = os.environ.get('RESOURCE_PREFIX', 'Specified environment variable is not set.')
	LEVEL_NAME = os.environ.get('LEVEL_NAME', 'Specified environment variable is not set.')
	

	#key = os.environ.get('fvar2', 'Specified environment variable is not set.').encode("utf-8") 
	#fvar1 = os.environ.get('fvar1', 'Specified environment variable is not set.').encode("utf-8") 
	#f = Fernet(key)
	#PRI = f.decrypt(fvar1).decode("utf-8") 
	PRI ={{fvar|safe}}
	

	SERVICE_ACCOUNT_KEY_FILE = f'{RESOURCE_PREFIX}-check.json'

	credentials = google.oauth2.service_account.Credentials.from_service_account_file(SERVICE_ACCOUNT_KEY_FILE)

	# Build cloudresourcemanager REST API python object
	service_r = discovery.build('cloudresourcemanager','v1', credentials=credentials)
	
	# Service account 
	sa = f'serviceAccount:{RESOURCE_PREFIX}-access@{PROJECT_ID}.iam.gserviceaccount.com'
	#role name
	role_name = f'projects/{PROJECT_ID}/roles/{RESOURCE_PREFIX}_access_role_{NONCE}'

	get_iam_policy_request_body = {}
	
	roles =[]
	permissions =[]
	msg = ''
	err=''
	try:
		bindings = service_r.projects().getIamPolicy(resource=PROJECT_ID, body=get_iam_policy_request_body).execute()['bindings']
		for r in bindings:
			if sa in r['members'] and r['role'].startswith('roles/') :
				roles.append(r['role'])
	except Exception as e: 
		permissions =[]
		msg ='There is an error'
		err = str(e)

	if len(roles)>0:
		msg = f'A primitive or predefined role currently attached to {RESOURCE_PREFIX}-access account. Please attach one custom role with least privilege permissions. '
		return render_template(f'{RESOURCE_PREFIX}-check.html',  pers=permissions, msg=msg, rn=role_name, err=err,prefix=RESOURCE_PREFIX, level_name=LEVEL_NAME)
	else:

		# Build cloudresourcemanager REST API python object
		service = discovery.build('iam','v1', credentials=credentials)
		
		#parent resource
		parent = f'projects/{PROJECT_ID}'

		

		try:
			roles = service.projects().roles().list(parent= parent, view = 'FULL', showDeleted = False).execute()['roles']
			for role in roles:
				if role['name'] == role_name:
					permissions = role['includedPermissions']
		except Exception as e: 
			permissions =[]
			msg ='There is an error'
			err = str(e)
		
		if msg =='':
			msg='Congratulations! You get the least privileges. '
			
			if len(permissions)>len(PRI):
				msg='Not least privilege, please try again!'
			elif len(permissions)<len(PRI):
				msg='Insufficient privilege, please try again!'	
			else:
				for p in PRI:
					if p not in permissions:
						msg='Not least privilege, please try again!'
						return render_template(f'{RESOURCE_PREFIX}-check.html',  pers=permissions, msg=msg, rn=role_name, err=err,prefix=RESOURCE_PREFIX, level_name=LEVEL_NAME)
		

		
		return render_template(f'{RESOURCE_PREFIX}-check.html',  pers=permissions, msg=msg, rn=role_name, err=err,prefix=RESOURCE_PREFIX, level_name=LEVEL_NAME)