from flask import render_template
def main(request):
	from googleapiclient import discovery
	import google.auth
	import os
	import collections 
	#from cryptography.fernet import Fernet

	
	# Set the project ID
	PROJECT_ID = os.environ['GCP_PROJECT']
	
	# Get function env variable
	NONCE = os.environ.get('NONCE', 'NONCE is not set.')
	LOGIN_USER = os.environ.get('LOGIN_USER', 'LOGIN_USER is not set.')
	FUNCTION_REGION = os.environ.get('FUNCTION_REGION', 'FUNCTION_REGION is not set.')

	ANWS ={{anws|safe}}
	LEVEL_NAMES = {{level_names|safe}}

	err=''
	total = 10 * len(LEVEL_NAMES)
	sum_score = 0

	scores = {}
	levels_sa = {}
	level_bindings ={}
	a_urls = {}
	c_urls = {}

	for k in LEVEL_NAMES:
		scores[k] = 0
		# Level Service Accounts 
		levels_sa[k] = f'serviceAccount:{k}-f-access-{NONCE}-sa@{PROJECT_ID}.iam.gserviceaccount.com'
		level_bindings[k] = []
		a_urls[k] = f'https://{FUNCTION_REGION}-{PROJECT_ID}.cloudfunctions.net/{k}-f-access-{NONCE}'
		c_urls[k] = f'https://europe-west1-{PROJECT_ID}.cloudfunctions.net/{k}-f-check-{NONCE}'

	


	# Get credential of cloud function account
	credentials, project_id = google.auth.default()


	
	# Get all level access account bindings
	try:
		# Build cloudresourcemanager REST API python object
		service_c = discovery.build('cloudresourcemanager','v1', credentials=credentials)
		get_iam_policy_request_body = {}
		bindings = service_c.projects().getIamPolicy(resource=PROJECT_ID, body=get_iam_policy_request_body).execute()['bindings']
		for l in levels_sa:
			for b in bindings:
				if levels_sa[l] in b['members']:
					level_bindings[l].append(b['role'])
	except Exception as e: 
		err = str(e)
	
	# Gel project custom roles and permissions
	try:
		# Build iam REST API python object
		service_i = discovery.build('iam','v1', credentials=credentials)	
		#parent resource
		parent = f'projects/{PROJECT_ID}'

		roles = service_i.projects().roles().list(parent= parent, view = 'FULL', showDeleted = False).execute()['roles']
		
						
	except Exception as e: 
		err = str(e)

	for l in ANWS:	
		if l.startswith('p'):
			if len(level_bindings[l])==len(ANWS[l]) and collections.Counter(level_bindings[l]) == collections.Counter(ANWS[l]):
				scores[l] += 10 
				sum_score += scores[l]

		else:
			#role name
			role_name = f'projects/{PROJECT_ID}/roles/{l}_access_role_{NONCE}'
			if 'predefined' not in ANWS[l]:
				if len(level_bindings[l])==1 and level_bindings[l][0] == role_name:
					for role in roles:
						if role['name'] == role_name:
							permissions = role['includedPermissions']
							if len(permissions)==len(ANWS[l]):
								least = True
								for p in ANWS[l]:
									if p not in permissions:
										least = False
										break	
								if least == True:
									scores[l] += 10	
									sum_score += scores[l]
			else: # level with misture of custom role and predefined role (used for ct5 but no level fits in this category anymore)
				if role_name in level_bindings[l]:
					correct_bindings = [role_name]
					correct_bindings.extend(ANWS[l]['predefined'])
					if len(level_bindings[l])==len(correct_bindings) and collections.Counter(level_bindings[l]) == collections.Counter(correct_bindings):
						scores[l] += 5 
						sum_score += scores[l]

					for role in roles:
						if role['name'] == role_name:
							permissions = role['includedPermissions']
							if len(permissions)==len(ANWS[l]['custom']):
								least = True
								for p in ANWS[l]['custom']:
									if p not in permissions:
										least = False
										break	
								if least == True:
									scores[l] += 5	
									sum_score += scores[l]

	return render_template(f'scores.html', scores=scores, user=LOGIN_USER, err=err, level_names=LEVEL_NAMES, total=total, sum_score=sum_score,nonce=NONCE,c_urls=c_urls,a_urls=a_urls )