#! /usr/bin/env python3

import sys
sys.path.append('.')
import os
import traceback
import argparse
import zipfile
# import settings
# import django
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "settings")

import django
django.setup()

from autograder.models import Course, Submission

import autograder.shared.utilities as ut


def main():
    args = parse_args()

    course = Course.objects.get(name=args.course_name)
    semester = course.semesters.get(name=args.semester_name)
    project = semester.projects.get(name=args.project_name)

    submissions = Submission.get_most_recent_submissions(project)
    with zipfile.ZipFile(args.archive_name, 'w') as z:
        for s in submissions:
            archive_dirname = '_'.join(sorted(s.submission_group.members))
            with ut.ChangeDirectory(ut.get_submission_dir(s)):
                for filename in s.get_submitted_file_basenames():
                    target_name = os.path.join(archive_dirname, filename)
                    print(target_name)
                    z.write(filename, arcname=target_name)


def parse_args():
    parser = argparse.ArgumentParser()
    parser.add_argument('course_name')
    parser.add_argument('semester_name')
    parser.add_argument('project_name')
    parser.add_argument('archive_name')

    return parser.parse_args()


if __name__ == '__main__':
    main()
