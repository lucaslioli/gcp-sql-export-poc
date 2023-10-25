import os
import logging
import argparse
import pandas as pd
import pymysql
import sqlalchemy

from dotenv import load_dotenv
from google.cloud.sql.connector import Connector, IPTypes


def connect_with_connector(connector) -> sqlalchemy.engine.base.Engine:
    """
    Initializes a connection pool for a Cloud SQL instance of MySQL.
    Uses the Cloud SQL Python Connector package.
    """
    try:
        logging.info("Connecting to Cloud SQL instance...")

        def getconn() -> pymysql.connections.Connection:
            conn = connector.connect(
                os.environ["CLOUD_SQL_CONNECTION_NAME"], 
                "pymysql",
                user=os.environ["DB_USER"],
                password=os.environ["DB_PASS"],
                db=os.environ["DB_NAME"],
            )
            return conn

        pool = sqlalchemy.create_engine(
            "mysql+pymysql://",
            creator=getconn,
        )
        return pool
    
    except Exception as e:
        logging.info("Error connecting to database:", e)
        return None


def create_table(pool: sqlalchemy.engine.base.Engine) -> bool:
    """
    Creates a table on the Cloud SQL instance.
    """
    try:
        # Read ddl from file
        with open(os.environ["DDL_FILE_PATH"], "r") as f:
            ddl = f.read()

        with pool.connect() as db_conn:
            db_conn.execute(
                sqlalchemy.text("DROP TABLE {}".format(os.environ["TABLE_NAME"]))
            )

            db_conn.execute(
                sqlalchemy.text(ddl)
            )

        return True
    
    except Exception as e:
        logging.info("Error creating table:", e)
        return False


def chunker(seq, size):
    """
    Helper function to chunk a dataframe into smaller dataframes.
    """
    return (seq[pos:pos + size] for pos in range(0, len(seq), size))


def populate_table(pool: sqlalchemy.engine.base.Engine) -> bool:
    """
    Populates the table on the Cloud SQL instance.
    """
    try:
        logging.info("Reading data from csv file...")
        with open(os.environ["CSV_FILE_PATH"], newline='', errors ='replace') as csvfile:
            logging.info("Creating dataframe...")
            df = pd.read_csv(csvfile)

        logging.info("Populating table...")
        with pool.connect() as db_conn:
            df.to_sql(con=db_conn, 
                      name=os.environ["TABLE_NAME"],
                      index=False,
                      if_exists="replace")
                
        return True
    
    except Exception as e:
        logging.error("ERROR populating table: %s", e)
        return False


if __name__ == '__main__':

    parser = argparse.ArgumentParser()
    parser.add_argument("-log",
                        "--loglevel",
                        default="warning",
                        help="Set logging level. e.g. -log debug, default=warning")
    
    args = parser.parse_args()

    logging.basicConfig(level=args.loglevel.upper())
    logging.info("Logging now setup.")

    load_dotenv()

    if os.environ.get('PROJECT_ID') is None:
        raise "PROJECT_ID environment variable not set."

    try:

        print("Starting...")

        ip_type = IPTypes.PRIVATE if os.environ.get("PRIVATE_IP") else IPTypes.PUBLIC

        connector = Connector(ip_type)

        pool = connect_with_connector(connector)

        if pool:
            logging.info("Connection pool created successfully\n")

        if create_table(pool):
            logging.info("Table created successfully\n")

        if populate_table(pool):
            logging.info("Table populated successfully\n")

    except Exception as e:
        logging.error("Unexpected error: %s", e)

    finally:
        connector.close()
        logging.info("Cloud SQL connection closed.\n")
        print("Finished.")
