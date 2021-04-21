import requests
DB_NAME = '{{ db_name }}'

def main(request):
    # vulnerable function here that exposes it's auth token
