from flask import render_template
def main(request):
	from googleapiclient import discovery
	import google.oauth2.service_account
	from google.oauth2.credentials import Credentials
	import os
	#from cryptography.fernet import Fernet
	
	# Set the project ID
	PROJECT_ID = os.environ['GCP_PROJECT']
	
	# Get function env variable
	NONCE = os.environ.get('NONCE', 'Specified environment variable is not set.')
	RESOURCE_PREFIX = os.environ.get('RESOURCE_PREFIX', 'Specified environment variable is not set.')
	LEVEL_NAME = os.environ.get('LEVEL_NAME', 'Specified environment variable is not set.')

	
	PRI = {{fvar|safe}}
	P_PRI = PRI['predefined']
	C_PRI = PRI['custom']
	
	#pri="".join(PRI.split()).split(',')

	SERVICE_ACCOUNT_KEY_FILE = f'{RESOURCE_PREFIX}-check.json'
	credentials = google.oauth2.service_account.Credentials.from_service_account_file(SERVICE_ACCOUNT_KEY_FILE)

	# Build cloudresourcemanager REST API python object
	service_r = discovery.build('cloudresourcemanager','v1', credentials=credentials)
	#role name
	role_name = f'projects/{PROJECT_ID}/roles/{RESOURCE_PREFIX}_access_role_{NONCE}'
	#parent resource
	parent = f'projects/{PROJECT_ID}'

	# Service account 
	sa = f'serviceAccount:{RESOURCE_PREFIX}-access@{PROJECT_ID}.iam.gserviceaccount.com'

	get_iam_policy_request_body = {}
	
	p_roles =[]
	c_roles = []
	permissions ={}
	msg = ''
	err=''
	try:
		bindings = service_r.projects().getIamPolicy(resource=PROJECT_ID, body=get_iam_policy_request_body).execute()['bindings']
		for r in bindings:
			if sa in r['members'] and r['role'].startswith('roles/') :
				p_roles.append(r['role'])
				permissions[r['role']]=[]
			if sa in r['members'] and r['role'].startswith(f'projects/{PROJECT_ID}/roles/') :
				c_roles.append(r['role'])
				permissions[r['role']]=[]
	except Exception as e: 
		msg ='There is an error'
		err = str(e)
		return render_template(f'{RESOURCE_PREFIX}-check.html',  pers=permissions, msg=msg, err=err, prefix=RESOURCE_PREFIX,level_name=LEVEL_NAME,nonce=NONCE)
	
	# Build iam  REST API python object
	service_i = discovery.build('iam','v1', credentials=credentials)
	
	try:
		for rn in p_roles:
			permissions[rn] = service_i.roles().get(name=rn).execute()["includedPermissions"]
	except Exception as e: 
		msg ='There is an error'
		err = str(e)
		return render_template(f'{RESOURCE_PREFIX}-check.html',  pers=permissions, msg=msg, err=err, prefix=RESOURCE_PREFIX,level_name=LEVEL_NAME,nonce=NONCE)

	if len(c_roles)==0:
		msg = f'Did not find custom role attached to {RESOURCE_PREFIX}-access Role '
		return render_template(f'{RESOURCE_PREFIX}-check.html',  pers=permissions, msg=msg, rn=role_name, err=err,prefix=RESOURCE_PREFIX, level_name=LEVEL_NAME, nonce=NONCE)
	elif len(c_roles)==1 and c_roles[0] != role_name :
		msg = f'Custom role {c_roles[0]} currently attached to {RESOURCE_PREFIX}-access Role. Need custom role {role_name}.'
		return render_template(f'{RESOURCE_PREFIX}-check.html',  pers=permissions, msg=msg, rn=role_name, err=err,prefix=RESOURCE_PREFIX, level_name=LEVEL_NAME, nonce=NONCE)	
	elif len(c_roles)>1:
		msg = f'More than one custom roles attached to {RESOURCE_PREFIX}-access account. Please only attach one.'
		return render_template(f'{RESOURCE_PREFIX}-check.html',  pers=permissions, msg=msg, rn=role_name, err=err,prefix=RESOURCE_PREFIX, level_name=LEVEL_NAME, nonce=NONCE)
		
	else:
		
		try:
			roles = service_i.projects().roles().list(parent= parent, view = 'FULL', showDeleted = False).execute()['roles']
			for role in roles:
				if role['name'] == role_name:
					permissions[role_name] = role['includedPermissions']
					
		except Exception as e: 
			msg ='There is an error'
			err = str(e)
			

		if msg =='':
			if len(p_roles)!=len(P_PRI):
				msg='Incorrect number of predefined roles, please try again!'
				return render_template(f'{RESOURCE_PREFIX}-check.html',  pers=permissions, msg=msg, err=err, prefix=RESOURCE_PREFIX,level_name=LEVEL_NAME,nonce=NONCE)
			else:
				msg='Congratulations! You get the least privileges. '
				for p in P_PRI:
					if p not in p_roles:
						msg='Incorrect predefined role, please try again!'
						return render_template(f'{RESOURCE_PREFIX}-check.html',  pers=permissions, msg=msg, err=err, prefix=RESOURCE_PREFIX,level_name=LEVEL_NAME,nonce=NONCE)
				for p in C_PRI:
					if p not in permissions[role_name]:
						msg='Not least privileges in custom role, please try again!'
						return render_template(f'{RESOURCE_PREFIX}-check.html',  pers=permissions, msg=msg, rn=role_name, err=err,prefix=RESOURCE_PREFIX, level_name=LEVEL_NAME, nonce=NONCE)
		
	
		return render_template(f'{RESOURCE_PREFIX}-check.html',  pers=permissions, msg=msg, err=err, prefix=RESOURCE_PREFIX,level_name=LEVEL_NAME,nonce=NONCE)