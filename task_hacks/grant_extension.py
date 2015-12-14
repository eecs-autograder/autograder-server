#! /usr/bin/env python3

import sys
sys.path.append('..')
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
# import autograder.core.models

from django.core.exceptions import ValidationError
from django.utils import timezone

from autograder.core.models import Course, SubmissionGroup


def main():
    args = parse_args()

    try:
        course = Course.objects.get(name=args.course_name)
        semester = course.semesters.get(name=args.semester_name)
        project = semester.projects.get(name=args.project_name)

        with transaction.atomic():
            group = None
            try:
                group = SubmissionGroup.objects.validate_and_create(
                    project=project, members=args.group_members)
            except ValidationError:
                group = SubmissionGroup.get_group(args.group_members, project)

            new_due_date = timezone.datetime(
                args.year, args.month, args.day,
                args.hour, args.minute, args.second, 0,
                # HACK: hardcoded timezone
                timezone.pytz.timezone('UTC'))
            print(new_due_date)
            group.extended_due_date = new_due_date

            group.save()

        print('extension granted')
    except Exception:
        traceback.print_exc()
    except KeyboardInterrupt:
        return


def parse_args():
    parser = argparse.ArgumentParser()
    parser.add_argument("course_name")
    parser.add_argument('semester_name')
    parser.add_argument('project_name')

    parser.add_argument('year', type=int)
    parser.add_argument('month', type=int)
    parser.add_argument('day', type=int)
    parser.add_argument('hour', type=int)
    parser.add_argument('minute', type=int)
    parser.add_argument('second', type=int)

    parser.add_argument('group_members', nargs='+')

    return parser.parse_args()

if __name__ == '__main__':
    main()
