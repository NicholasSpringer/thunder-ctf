import os
import sqlalchemy
import google.auth

def init_connection_engine():
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

    return init_tcp_connection_engine(db_config)

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
    from pprint import pprint

    from googleapiclient import discovery
    from oauth2client.client import GoogleCredentials

    credentials, project_id = google.auth.default()

    service = discovery.build('sqladmin', 'v1beta4', credentials=credentials)



    request = service.instances().list(project=project_id)
    while request is not None:
        response = request.execute()

        for database_instance in response['items']:
            # TODO: Change code below to process each `database_instance` resource:
            pprint(database_instance)

        request = service.instances().list_next(previous_request=request, previous_response=response)

def init_tcp_connection_engine(db_config):
    # [START cloud_sql_postgres_sqlalchemy_create_tcp]
    # Remember - storing secrets in plaintext is potentially unsafe. Consider using
    # something like https://cloud.google.com/secret-manager/docs/overview to help keep
    # secrets secret.
    db_name = os.environ["DB_NAME"]
    db_host = os.environ["DB_HOST"]



    # Extract host and port from db_host
    host_args = db_host.split(":")
    db_hostname, db_port = host_args[0], int(host_args[1])

    pool = sqlalchemy.create_engine(
        # Equivalent URL:
        # postgres+pg8000://<db_user>:<db_pass>@<db_host>:<db_port>/<db_name>
        sqlalchemy.engine.url.URL(
            drivername="postgresql+pg8000",
            username="postgres",  # e.g. "my-database-user"
            password="Ax4**7^bBjwMz43*",  # e.g. "my-database-password"
            host=db_hostname,  # e.g. "127.0.0.1"
            port=db_port,  # e.g. 5432
            database="userdata-db"  # e.g. "my-database-name"
        ),
        **db_config
    )
    # [END cloud_sql_postgres_sqlalchemy_create_tcp]
    pool.dialect.description_encoding = None
    return pool

# This global variable is declared with a value of `None`, instead of calling
# `init_connection_engine()` immediately, to simplify testing. In general, it
# is safe to initialize your database connection pool when your script starts
# -- there is no need to wait for the first request.
db = None

#Table creation for  audit
def audit_create_tables():
    global db
    db = init_connection_engine()
    # Create tables (if they don't already exist)
    with db.connect() as conn:
        conn.execute(
            """CREATE TABLE users (
                ID       INT PRIMARY KEY   NOT NULL,
                NAME     TEXT              NOT NULL,
                PHONE    TEXT              NOT NULL,
                ADDRESS  TEXT              NOT NULL
            );"""
        )


def get_index_context():
    votes = []

    with db.connect() as conn:
        # Execute the query and fetch all results
        recent_votes = conn.execute(
            "SELECT candidate, time_cast FROM votes "
            "ORDER BY time_cast DESC LIMIT 5"
        ).fetchall()
        # Convert the results into a list of dicts representing votes
        for row in recent_votes:
            votes.append({
                'candidate': row[0],
                'time_cast': row[1]
            })

        stmt = sqlalchemy.text(
            "SELECT COUNT(vote_id) FROM votes WHERE candidate=:candidate")
        # Count number of votes for tabs
        tab_result = conn.execute(stmt, candidate="TABS").fetchone()
        tab_count = tab_result[0]
        # Count number of votes for spaces
        space_result = conn.execute(stmt, candidate="SPACES").fetchone()
        space_count = space_result[0]

    return {
        'space_count': space_count,
        'recent_votes': votes,
        'tab_count': tab_count,
    }


