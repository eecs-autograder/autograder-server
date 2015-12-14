#! /usr/bin/env python3

import os
import sys
# sys.path.append(os.path.dirname(os.path.abspath(__file__)))
sys.path.append('..')
# import traceback
import argparse
# import settings
# import django
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "settings")

import django
django.setup()

from autograder.core.models import Course, Submission


def main():
    args = parse_args()

    args = parse_args()

    course = Course.objects.get(name=args.course_name)
    semester = course.semesters.get(name=args.semester_name)
    project = semester.projects.get(name=args.project_name)

    submissions = Submission.get_most_recent_submissions(project)
    for submission in submissions:
        submission.show_all_test_cases_and_suites = True
        submission.save()


def parse_args():
    parser = argparse.ArgumentParser()
    parser.add_argument('course_name')
    parser.add_argument('semester_name')
    parser.add_argument('project_name')

    return parser.parse_args()


if __name__ == '__main__':
    main()
