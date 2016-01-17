#! /usr/bin/env python3

import argparse
import MySQLdb
import subprocess

"""
This script does the following:
    1. Starts the appropriate database server
    2. Creates a database with the specified name
    3. Creates a user that has full permissions on the database
"""


DB_USERNAME = 'autograder'


def main():
    args = parse_args()

    subprocess.call(['service', 'mysql', 'start'], timeout=10)
    _DB_HANDLERS[args.database_backend](args.database_name)


def parse_args():
    parser = argparse.ArgumentParser()
    parser.add_argument("database_backend", choices=['mysql'])
    parser.add_argument("database_name")

    return parser.parse_args()


def _init_mysql(db_name):
    server_connection = MySQLdb.connect()
    server_cursor = server_connection.cursor()
    # NOTE: The autograder database API ensures that db_name will only
    # contain alphabetic characters.
    server_cursor.execute('CREATE DATABASE {}'.format(db_name))
    server_cursor.execute('CREATE USER "{}"@"localhost"'.format(DB_USERNAME))
    server_cursor.execute(
        'GRANT ALL ON {}.* to "{}"'.format(db_name, DB_USERNAME))
    server_cursor.close()
    server_connection.commit()


# Map of string identifiers to handler functions
_DB_HANDLERS = {
    'mysql': _init_mysql
}


if __name__ == '__main__':
    main()
