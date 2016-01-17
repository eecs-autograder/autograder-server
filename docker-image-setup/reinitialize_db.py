#! /usr/bin/env python3

import argparse
import MySQLdb

"""
This script drops and re-creates the specified database
"""

DB_USERNAME = 'autograder'


def main():
    args = parse_args()

    _DB_HANDLERS[args.database_backend](args.database_name)


def parse_args():
    parser = argparse.ArgumentParser()
    parser.add_argument("database_backend", choices=['mysql'])
    parser.add_argument("database_name")

    return parser.parse_args()


def _reinitialize_mysql(db_name):
    server_connection = MySQLdb.connect()
    server_cursor = server_connection.cursor()
    # NOTE: The autograder database API ensures that db_name will only
    # contain alphabetic characters.
    server_cursor.execute('DROP DATABASE {}'.format(db_name))
    server_cursor.execute('CREATE DATABASE {}'.format(db_name))
    server_cursor.execute(
        'GRANT ALL ON {}.* to "{}"'.format(db_name, DB_USERNAME))
    server_cursor.close()
    server_connection.commit()


# Map of string identifiers to handler functions
_DB_HANDLERS = {
    'mysql': _reinitialize_mysql
}


if __name__ == '__main__':
    main()
