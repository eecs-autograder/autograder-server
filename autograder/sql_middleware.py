# Source: https://djangosnippets.org/snippets/290/
# Accessed Dec 1, 2017

from django.db import connection
from django.conf import settings
import os


class SqlPrintingMiddleware(object):
    # def process_response(self, request, response):
    #     # from sys import stdout
    #     # if stdout.isatty():
    #     for query in connection.queries:
    #         print("\033[1;31m[%s]\033[0m \033[1m%s\033[0m" % (query['time'],
    #                                                     " ".join(query['sql'].split())))
    #     return response

    """
    Middleware which prints out a list of all SQL queries done
    for each view that is processed.  This is only useful for debugging.
    """
    def process_response(self, request, response):
        indentation = 2
        if len(connection.queries) > 0 and settings.DEBUG:
            total_time = 0.0
            for query in connection.queries:
                nice_sql = query['sql'].replace('"', '').replace(',',', ')
                sql = "\033[1;31m[%s]\033[0m %s" % (query['time'], nice_sql)
                total_time += float(query['time'])
                print("%s%s\n" % (" "*indentation, sql))
            replace_tuple = (" "*indentation, str(total_time))
            print("%s\033[1;32m[TOTAL TIME: %s seconds]\033[0m" % replace_tuple)
        return response
