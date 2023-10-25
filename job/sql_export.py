# Copyright 2019 Google LLC
# Code based on https://gist.github.com/rasmi/975e4d7fda435bb6807c14b0fffcf82b

"""Export Cloud SQL databases to CSV files on GCS."""

import os
import logging
import argparse
import time

import google.auth
import googleapiclient.errors
from googleapiclient import discovery

from dotenv import load_dotenv


SECONDS_BETWEEN_STATUS_CHECKS = 5


_client = None
def client():
    global _client
    if not _client:
        credentials, _ = google.auth.default()
        _client = discovery.build(
            'sqladmin', 'v1', credentials=credentials)
    return _client


def create_export_context(export_uri, export_query, db_name):
    """Creates the exportContext configuration for the export operation.
    See here for details:
        https://cloud.google.com/sql/docs/mysql/admin-api/rest/v1/instances/export
    Args:
        export_uri: GCS URI to write the exported CSV data to.
        export_query: SQL query defining the data to be exported.
        db_name: Cloud SQL Database name.
    Returns:
        export_context dict which can be passed to client.instances.export().
    """

    export_context = {
        'exportContext': {
            'kind': 'sql#exportContext',
            'fileType': 'CSV',
            'uri': export_uri,
            'databases': [db_name],
            'csvExportOptions': {
                'selectQuery': export_query
            }
        }
    }

    return export_context


def wait_until_operation_finished(project_id, operation_id):
    """Monitor a Cloud SQL operation's progress and wait until it completes.
    We must wait until completion becuase only one Cloud SQL operation can run
    at a time.
    Args:
        project_id: GCP Project ID.
        operation_id: Cloud SQL Operation ID.
    Returns:
        True if operation succeeded without errors, False if not.
    See here for details:
        https://cloud.google.com/sql/docs/mysql/admin-api/rest/v1/operations/get
    """
    operation_in_progress = True
    operation_success = False

    while operation_in_progress:
        get_operation = client().operations().get(
            project=project_id, operation=operation_id)
        
        operation = get_operation.execute()
        operation_status = operation['status']

        if operation_status in {'PENDING', 'RUNNING', 'UNKNOWN'}:
            time.sleep(SECONDS_BETWEEN_STATUS_CHECKS)
        elif operation_status == 'DONE':
            operation_in_progress = False

        logging.debug("Operation [%s] status: [%s]",
                      operation_id, operation_status)

    if 'error' in operation:
        errors = operation['error'].get('errors', [])
        for error in errors:
            logging.error(
                "Operation %s finished with error: %s, %s\n%s",
                operation_id,
                error.get('kind'),
                error.get('code'),
                error.get('message'))
    else:
        logging.info("Operation [%s] succeeded.", operation_id)
        operation_success = True

    return operation_success


def export_table(
        project_id, instance_id, db_name, table_name, export_query, export_uri):
    """Export a Cloud SQL table to a CSV file on GCS.
    Execute the export operation and wait until it completes.
    Args:
        project_id: GCP Project ID.
        instance_id: Cloud SQL Instance ID.
        db_name: Cloud SQL Database name.
        table_name: Table to export.
        export_query: Query to export (usually 'SELECT * FROM table').
        export_uri: GCS URI to export to.
    Returns:
        True if operation succeeded without errors, False if not.
    """

    export_context = create_export_context(
        export_uri, export_query, db_name)

    export_request = client().instances().export(
        project=project_id,
        instance=instance_id,
        body=export_context)

    logging.info("Starting export: [%s]", str(export_request.to_json()))
    try:
        response = export_request.execute()
    
    except googleapiclient.errors.HttpError:
        logging.exception("Failed to export table [%s]", table_name)
        return False

    # We need to block until the operation is done because
    # the Cloud SQL API only supports one operation at a time.
    operation_id = response['name']
    logging.info("Waiting for export operation [%s] to complete for table [%s] "
                 "in database [%s] in project [%s]",
                 operation_id, table_name, instance_id, project_id)
    operation_success = wait_until_operation_finished(project_id, operation_id)

    return operation_success


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

        export_uri = "{}/{}.csv".format(os.environ["BUCKET_URI"], os.environ["TABLE_NAME"])
        export_query = "SELECT * FROM " + os.environ["TABLE_NAME"]

        export_table(project_id=os.environ["PROJECT_ID"],
                     instance_id=os.environ["INSTANCE_ID"],
                     db_name=os.environ["DB_NAME"],
                     table_name=os.environ["TABLE_NAME"],
                     export_query=export_query,
                     export_uri=export_uri)

        print("Finished.")

    except Exception as e:
        logging.error(e)
