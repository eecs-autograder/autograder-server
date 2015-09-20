#! /usr/bin/env python3

import sys
sys.path.append('.')
import os
# import traceback
# import time
import argparse
# import settings
# import django
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "settings")

import django
django.setup()
# from django.db import transaction
# from django.db.models import Max

# import autograder.models

from autograder.models import Course, Submission
# from autograder.autograder_sandbox import AutograderSandbox

import autograder.shared.utilities as ut


def main():
    args = parse_args()

    course = Course.objects.get(name=args.course_name)
    semester = course.semesters.get(name=args.semester_name)
    project = semester.projects.get(name=args.project_name)

    if args.all_final:
        submissions = [
            s for s in Submission.get_most_recent_submissions(project)
            if s.status != 'invalid'
        ]
        # for group in project.submission_groups.filter(project=project):
        #     group_subs = group.submissions.all().order_by('-_timestamp')
        #     if group_subs:
        #         sub = group_subs[0]
        #         if sub.status != 'invalid':
        #             submissions.append(group_subs[0])
    elif args.all_with_errors:
        submissions = Submission.objects.filter(
            status='error', submission_group__project=project)
    # elif args.specified_final is not None:
    #     groups = [group for group in groups if ]

    print('Re-running {} submissions...'.format(len(submissions)))

    for submission in submissions:
        print('{}-{}'.format(
            submission.submission_group.members,
            submission.timestamp.strftime(ut.FILESYSTEM_TIMESTAMP_FORMAT_STR))
        )
        submission.results.all().delete()
        submission.status = 'queued'
        submission.save()


def parse_args():
    parser = argparse.ArgumentParser()
    parser.add_argument('course_name')
    parser.add_argument('semester_name')
    parser.add_argument('project_name')

    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument('--all_final', '-F', action='store_true')
    # group.add_argument('--specified_final', '-s', nargs='+')
    group.add_argument(
        '--all_with_errors', '-E', action='store_true', required=False)

    return parser.parse_args()


if __name__ == '__main__':
    main()
