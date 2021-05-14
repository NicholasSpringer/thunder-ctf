import sqlalchemy
import google.auth
import subprocess
import time
import csv
from google.cloud import logging as glogging
from googleapiclient import discovery
from flask import Flask, request, Response
from sqlalchemy.sql import text

app = Flask(__name__)

logger = glogging.Client().logger("API-Engine")

credentials, project_id = google.auth.default()
service = discovery.build('sqladmin', 'v1beta4', credentials=credentials)
response = service.instances().list(project=project_id).execute()
connection_name = response['items'][0]['connectionName']

subprocess.Popen(['./cloud_sql_proxy', f'-instances={connection_name}=tcp:5432'])
time.sleep(5)

db_config = {
    "pool_size": 5,
    "max_overflow": 2,
    "pool_recycle": 1800,  # 30 minutes
}

db = sqlalchemy.create_engine(
    sqlalchemy.engine.url.URL(
        drivername="postgresql+pg8000",
        username="api-engine",
        password="psw",
        database="userdata-db",
        host='127.0.0.1',
        port=5432
    ),
    **db_config
)
db.dialect.description_encoding = None


@app.route("/", methods=["POST"])
def new_user():
    keys = request.form.keys()
    if 'name' not in keys or 'address' not in keys or 'phone' not in keys:
        payload = ''
        for key in request.form.keys():
            payload = payload + key + ' '
        logger.log_struct(
            {'endpoint': 'new user',
             'error': 'Invalid post: ' + payload})
        return Response(response='Request failed. Must include name, phone, and address in payload. keys:'+payload, status=400)
    
    try:
        with db.connect() as conn:
            stmt = text("INSERT INTO users (name, phone, address) VALUES (:name, :phone, :address)")
            conn.execute(stmt, name=request.form['name'], phone=request.form['phone'], address=request.form['address'])
    except Exception as e:
        return Response(response='Could not connect to database. error: ' + str(e) + ' db_conn: ' + connection_name, status=500)
        
    return Response(status=200, response='User added')


@app.route("/test", methods=["GET"])
def test():
    return "<p>hello test</p>"


@app.route("/follow", methods=["POST"])
def follow():
    keys = request.form.keys()
    if 'follower' not in keys or 'followee' not in keys:
        for key in request.form.keys():
            payload = payload + key + ' '
        logger.log_struct(
            {'endpoint': "follow",
             'error': "Invalid post: " + payload})
        return Response(response='Request failed. Must include follower and followee:'+payload, status=400)

    try:
        #check if already following 
        with db.connect() as conn:
            stmt = text("INSERT INTO follows (follower, followee) VALUES (:follower, :followee)")
            conn.execute(stmt, follower=int(request.form['follower']), followee=int(request.form['followee']))
    except Exception as e:
        return Response(response='Could not connect to database. error: ' + str(e) + ' db_conn: ' + connection_name, status=500)
        
    return Response(status=200, response='User followed')


@app.route("/delete", methods=["POST"])
def delete():
    keys = request.form.keys()
    if 'name' not in keys or 'user_id' not in keys:
        for key in request.form.keys():
            payload = payload + key + ' '
        logger.log_struct(
            {'endpoint': "delete",
             'error': "Invalid post: " + payload})
        return Response(response='Request failed. Must include user\'s name and user_id:'+payload, status=400)

    try:
        #attempt to delete user
        with db.connect() as conn:
            stmt = text("DELETE FROM users WHERE name = :name AND user_id = :user_id")
            conn.execute(stmt, user_id=request.form['user_id'], name=request.form['name'])
    except Exception as e:
        return Response(response='Could not connect to database. error: ' + str(e) + ' db_conn: ' + connection_name, status=500)
        
    return Response(status=200, response='User deleted')

if __name__ == "__main__":
    app.run(host="127.0.0.1", port=80)
