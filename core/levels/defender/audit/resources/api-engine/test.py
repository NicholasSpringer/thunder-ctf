import google.auth
import sqlalchemy
import subprocess
import time
import csv
from googleapiclient import discovery
from sqlalchemy.sql import text

credentials, project_id = google.auth.default()
service = discovery.build('sqladmin', 'v1beta4', credentials=credentials)
response = service.instances().list(project=project_id).execute()
instance_name = response['items'][0]['connectionName']

#subprocess.Popen(['./cloud_sql_proxy', f'-instances={instance_name}=tcp:5432'])
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

devs = csv.DictReader(open('devs.csv', newline=''))
with db.connect() as conn:
    conn.execute(
            """
            CREATE TABLE users (
                user_id  SERIAL PRIMARY KEY,
                name     TEXT              NOT NULL,
                phone    TEXT              NOT NULL,
                address  TEXT              NOT NULL
            );
            CREATE TABLE devs (
                dev_id   SERIAL PRIMARY KEY,
                name     TEXT              NOT NULL,
                phone    TEXT              NOT NULL,
                address  TEXT              NOT NULL
            );
            CREATE TABLE follows (
                friend_id SERIAL PRIMARY KEY,
                follower INT   NOT NULL REFERENCES users(user_id),
                followee INT   NOT NULL REFERENCES users(user_id)
            );
        """
    )

    for dev in devs:
        stmt = text("INSERT INTO devs (name, phone, address) VALUES (:name, :phone, :address)")
        conn.execute(stmt, dev)
