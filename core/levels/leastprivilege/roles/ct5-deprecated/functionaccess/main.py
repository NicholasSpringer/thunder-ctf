#https://github.com/GoogleCloudPlatform/python-docs-samples/blob/master/codelabs/flex_and_vision/main.py
from flask import render_template,redirect
def main(request):
	import google.auth
	from google.cloud import datastore, storage, vision
	import os
	from datetime import datetime
	
	
	# Set the project ID
	PROJECT_ID = os.environ['GCP_PROJECT']
	FUNCTION_REGION = os.environ['FUNCTION_REGION']
	NONCE = os.environ.get('NONCE', 'Specified environment variable is not set.')
	RESOURCE_PREFIX = os.environ.get('RESOURCE_PREFIX', 'Specified environment variable is not set.')
	LEVEL_NAME = os.environ.get('LEVEL_NAME', 'Specified environment variable is not set.')

	CLOUD_STORAGE_BUCKET = f'{RESOURCE_PREFIX}-bucket-{NONCE}'
	KIND =  f'{RESOURCE_PREFIX}-{NONCE}-{PROJECT_ID}'

	# Get credential of cloud function account
	credentials, project_id = google.auth.default()

	#score function url
	surl  = f'https://{FUNCTION_REGION}-{PROJECT_ID}.cloudfunctions.net/scores-f-{NONCE}'
	#check function url
	url=f'https://europe-west1-{PROJECT_ID}.cloudfunctions.net/{RESOURCE_PREFIX}-f-check-{NONCE}'
	#upload url
	up_url = f'/{RESOURCE_PREFIX}-f-access-{NONCE}'
	#err_build=request.args['err_build'] if request.args and 'err_build' in request.args else ''
	err_build = ''
	err_query=''
	image_entities = []
	
	if request.files and 'file' in request.files:
		
		try:
			
			photo = request.files['file']

			# Create a Cloud Storage client.
			storage_client = storage.Client(credentials=credentials)

			# Get the bucket that the file will be uploaded to.
			bucket = storage_client.get_bucket(CLOUD_STORAGE_BUCKET)

			# Create a new blob and upload the file's content.
			blob = bucket.blob(photo.filename)
			blob.upload_from_string(photo.read(), content_type=photo.content_type)

			# Make the blob publicly viewable.
			blob.make_public()

			# Create a Cloud Vision client.
			vision_client = vision.ImageAnnotatorClient()

			# Use the Cloud Vision client to detect a face for our image.
			source_uri = 'gs://{}/{}'.format(CLOUD_STORAGE_BUCKET, blob.name)
			image = vision.Image(source=vision.ImageSource(gcs_image_uri=source_uri))
			faces = vision_client.face_detection(image).face_annotations

			# If a face is detected, save to Datastore the likelihood that the face
			# displays 'joy,' as determined by Google's Machine Learning algorithm.
			if len(faces) > 0:
				face = faces[0]

				# Convert the likelihood string.
				likelihoods = [
					'Unknown', 'Very Unlikely', 'Unlikely', 'Possible', 'Likely',
					'Very Likely']
				face_joy = likelihoods[face.joy_likelihood]
			else:
				face_joy = 'Unknown'

			# Create a Cloud Datastore client.
			datastore_client = datastore.Client(credentials=credentials)

			# Fetch the current date / time.
			current_datetime = datetime.now()

			# The kind for the new entity.
			kind = KIND

			# The name/ID for the new entity.
			name = blob.name

			# Create the Cloud Datastore key for the new entity.
			key = datastore_client.key(kind, name)

			# Construct the new entity using the key. Set dictionary values for entity
			# keys blob_name, storage_public_url, timestamp, and joy.
			entity = datastore.Entity(key)
			entity['blob_name'] = blob.name
			entity['image_public_url'] = blob.public_url
			entity['timestamp'] = current_datetime
			entity['joy'] = face_joy

			# Save the new entity to Datastore.
			datastore_client.put(entity)
		except Exception as e:
			err_build = str(e)

		if err_build == '':
			return redirect(up_url)

	try:
		#Build datastore REST API python object
		client = datastore.Client(credentials=credentials )
		# Use the Cloud Datastore client to fetch information from Datastore about each photo.
		query = client.query(kind=KIND)
		image_entities = list(query.fetch())

	except Exception as e:
		err_query=str(e)
	
	
	
	return render_template(f'{RESOURCE_PREFIX}-access.html', url=url, 
                err_build=err_build,err_query=err_query,prefix=RESOURCE_PREFIX, level_name=LEVEL_NAME, 
                nonce=NONCE,surl=surl,image_entities=image_entities,up_url=up_url)

	

