#! /usr/bin/env python3

import sys
import os
import traceback
import argparse
import zipfile
# import settings
# import django
sys.path.append('..')
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "settings")

import django  # noqa
django.setup()

from autograder.core.models import Course, Submission  # noqa

import autograder.core.shared.utilities as ut  # noqa


def main():
    args = parse_args()

    course = Course.objects.get(name=args.course_name)
    semester = course.semesters.get(name=args.semester_name)
    project = semester.projects.get(name=args.project_name)

    submissions = Submission.get_most_recent_submissions(project)
    with zipfile.ZipFile(args.archive_name, 'w') as z:
        for s in submissions:
            if not args.include_staff and is_staff_submission(s, semester):
                continue

            archive_dirname = '_'.join(sorted(s.submission_group.members))
            with ut.ChangeDirectory(ut.get_submission_dir(s)):
                for filename in s.get_submitted_file_basenames():
                    target_name = os.path.join(
                        '{}_{}_{}'.format(
                            course.name, semester.name, project.name),
                        archive_dirname, filename)
                    print(target_name)
                    z.write(filename, arcname=target_name)


def parse_args():
    parser = argparse.ArgumentParser()
    parser.add_argument('course_name')
    parser.add_argument('semester_name')
    parser.add_argument('project_name')
    parser.add_argument('archive_name')

    parser.add_argument(
        '--include_staff', '-s', action='store_true', default=False)

    return parser.parse_args()


def is_staff_submission(submission, semester):
    for username in submission.submission_group.members:
        if semester.is_semester_staff(username):
            return True

    return False


if __name__ == '__main__':
    main()
