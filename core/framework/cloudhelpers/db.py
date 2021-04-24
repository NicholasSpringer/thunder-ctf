import os
import sqlalchemy
import google.auth
from pprint import pprint
from googleapiclient import discovery

def init_connection_engine(db_name):
    db_config = {
        # [START cloud_sql_postgres_sqlalchemy_limit]
        # Pool size is the maximum number of permanent connections to keep.
        "pool_size": 5,
        # Temporarily exceeds the set pool_size if no connections are available.
        "max_overflow": 2,
        # The total number of concurrent connections for your application will be
        # a total of pool_size and max_overflow.
        # [END cloud_sql_postgres_sqlalchemy_limit]

        # [START cloud_sql_postgres_sqlalchemy_backoff]
        # SQLAlchemy automatically uses delays between failed connection attempts,
        # but provides no arguments for configuration.
        # [END cloud_sql_postgres_sqlalchemy_backoff]

        # [START cloud_sql_postgres_sqlalchemy_timeout]
        # 'pool_timeout' is the maximum number of seconds to wait when retrieving a
        # new connection from the pool. After the specified amount of time, an
        # exception will be thrown.
        "pool_timeout": 30,  # 30 seconds
        # [END cloud_sql_postgres_sqlalchemy_timeout]

        # [START cloud_sql_postgres_sqlalchemy_lifetime]
        # 'pool_recycle' is the maximum number of seconds a connection can persist.
        # Connections that live longer than the specified amount of time will be
        # reestablished
        "pool_recycle": 1800,  # 30 minutes
        # [END cloud_sql_postgres_sqlalchemy_lifetime]
    }

    return init_tcp_connection_engine(db_config, db_name)

def get_db_hostname():
    """
    BEFORE RUNNING:
    ---------------
    1. If not already done, enable the Cloud SQL Administration API
    and check the quota for your project at
    https://console.developers.google.com/apis/api/sqladmin
    2. This sample uses Application Default Credentials for authentication.
    If not already done, install the gcloud CLI from
    https://cloud.google.com/sdk and run
    `gcloud beta auth application-default login`.
    For more information, see
    https://developers.google.com/identity/protocols/application-default-credentials
    3. Install the Python client library for Google APIs by running
    `pip install --upgrade google-api-python-client`
    """
    credentials, project_id = google.auth.default()

    service = discovery.build('sqladmin', 'v1beta4', credentials=credentials)



    request = service.instances().list(project=project_id)
    while request is not None:
        response = request.execute()

        for database_instance in response['items']:
            # TODO: Change code below to process each `database_instance` resource:
            pprint(database_instance)
            return database_instance

        request = service.instances().list_next(previous_request=request, previous_response=response)

def init_tcp_connection_engine(db_config, db_name):
    # [START cloud_sql_postgres_sqlalchemy_create_tcp]
    # Remember - storing secrets in plaintext is potentially unsafe. Consider using
    # something like https://cloud.google.com/secret-manager/docs/overview to help keep
    # secrets secret.




    # Extract host and port from db_host
    db_stuff = get_db_hostname()

    db_hostname = db_stuff["ipAddresses"][0]["ipAddress"]
    db_port = 5432

    pool = sqlalchemy.create_engine(
        # Equivalent URL:
        # postgres+pg8000://<db_user>:<db_pass>@<db_host>:<db_port>/<db_name>
        sqlalchemy.engine.url.URL(
            drivername="postgresql+pg8000",
            username="postgres",  # e.g. "my-database-user"
            password="psw",  # e.g. "my-database-password"
            host=db_hostname,  # e.g. "127.0.0.1"
            port=db_port,  # e.g. 5432
            database=db_name  # e.g. "my-database-name"
        ),
        **db_config
    )
    # [END cloud_sql_postgres_sqlalchemy_create_tcp]
    pool.dialect.description_encoding = None
    return pool

#Connect to DB
def connect(db_name):
    return init_connection_engine(db_name)


