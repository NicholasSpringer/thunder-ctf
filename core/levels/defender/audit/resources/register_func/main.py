import sqlalchemy
import google.auth
import logging
import subprocess
import time
import csv
from googleapiclient import discovery
from flask import Flask, request, Response
from sqlalchemy.sql import text

app = Flask(__name__)

logger = logging.getLogger()

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
        return Response(response='Request failed. Must include name, phone, and address in payload. keys:'+payload, status=400)
    
    try:
        with db.connect() as conn:
            stmt = text("INSERT INTO users (name, phone, address) VALUES (:name, :phone, :address)")
            conn.execute(stmt, name=request.form['name'], phone=request.form['phone'], address=request.form['address'])
    except Exception as e:
        logger.exception(e)
        return Response(response='Could not connect to database. error: ' + str(e) + ' db_conn: ' + connection_name, status=500)
        
    # vulnerable function here that exposes it's auth token
    return Response(status=200, response='User added')

if __name__ == "__main__":
    app.run(host="127.0.0.1", port=80)