import random
import sys
import os
import subprocess
import time
import json
import csv
import sqlalchemy
import google.auth
import requests
import urllib 

from googleapiclient import discovery
from sqlalchemy.sql import text
from google.oauth2 import service_account, id_token
from core.framework import levels
from google.cloud import storage, logging as glogging
from core.framework.cloudhelpers import (
    deployments,
    iam,
    gcstorage,
    cloudfunctions
)
import google.auth.transport.requests
from google.auth.transport.requests import AuthorizedSession
#os.environ['GOOGLE_APPLICATION_CREDENTIALS'] = 'start/dev-account.json'

def main():
    credentials, project_id = google.auth.default()
    nonce = sys.argv[1]

    url = "http://us-central1-" + project_id + ".cloudfunctions.net/rm-user-" + nonce

    req = google.auth.transport.requests.Request()
    id_token = google.oauth2.id_token.fetch_id_token(req, url)
    headers = {'Authorization': f"Bearer {id_token}"}
    data = {'name':'Robert Caldwell', 'authentication':'hjhadsfkjhgadsfkjhgaewkjygdasfjhgdfkjygadsjkygdakfjuygdfahjkygfdajskhygfy76t478t3487y3grewu7ydfg'}
    resp = req(url, method = 'POST', body = data, headers = headers)
    print(vars(resp))

main()
