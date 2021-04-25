import requests

def main(request):
    # vulnerable function here that exposes it's auth token
    return 'new user added\n'
