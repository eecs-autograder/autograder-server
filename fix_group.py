#! /usr/bin/env python3

import sys
sys.path.append('.')
import os
import traceback
# import time
import argparse
# import settings
# import django
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "settings")

import django
django.setup()
from django.db import transaction
# from django.db.models import Max
# import autograder.models

from autograder.models import Course, SubmissionGroup


def main():
    args = parse_args()

    try:
        course = Course.objects.get(name=args.course_name)
        semester = course.semesters.get(name=args.semester_name)
        project = semester.projects.get(name=args.project_name)

        with transaction.atomic():
            for member in args.new_members:
                group = project.submission_groups.get(
                    _members__contains=[member])
                group.delete()
            SubmissionGroup.objects.validate_and_create(
                project=project, members=args.new_members)

        print('group {} created'.format(args.new_members))
    except Exception:
        traceback.print_exc()
    except KeyboardInterrupt:
        return


def parse_args():
    parser = argparse.ArgumentParser()
    parser.add_argument("course_name")
    parser.add_argument('semester_name')
    parser.add_argument('project_name')

    parser.add_argument('new_members', nargs='+')

    return parser.parse_args()

if __name__ == '__main__':
    main()