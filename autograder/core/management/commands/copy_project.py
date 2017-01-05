#! /usr/bin/env python3

import csv
# import traceback

from django.core.management.base import BaseCommand

from autograder.core.models import Course


class Command(BaseCommand):
    help = 'Change to something helpful'

    def add_arguments(self, parser):
        parser.add_argument('course_name')
        parser.add_argument('project_name')
        parser.add_argument('target_course_name')

    def handle(self, course_name, project_name, target_course_name, *args, **kwargs):
        print(course_name, project_name, target_course_name)

    # load project
    # load target course
    # put into fn
    #
    # load thing
    # make dict, excluding things
    # pass dict to validate and create with unpacking syntax
    #
    #
    # 1. make project
    # 2. make patterns and files, passing in p
    # 3. Create ag test case and link to project, then link to pattern and file
    #   fields: test resource files, student resource files, project files to compile,
    #   student files to compile
    #
    # django doc on models (but always use validate_and_create and
    # validate_and_update)
