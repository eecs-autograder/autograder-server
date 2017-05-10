#! /usr/bin/env python3

import os
# import traceback
import zipfile

from django.core.management.base import BaseCommand

from autograder.core.models import Project

import autograder.core.utils as ut
import autograder.utils as misc_ut


class Command(BaseCommand):
    help = 'Saves a zip archive of ultimate submissions for the specified project'

    def add_arguments(self, parser):
        parser.add_argument('project_pk', type=int)
        parser.add_argument('archive_name')

        parser.add_argument(
            '--include_staff', '-s', action='store_true', default=False)

    def handle(self, *args, **options):
        project = Project.objects.get(pk=options['project_pk'])
        course = project.course

        groups = project.submission_groups.all()
        submissions = [group.ultimate_submission for group in groups if group.submissions.count()]
        with zipfile.ZipFile(options['archive_name'], 'w') as z:
            for s in submissions:
                if not options['include_staff'] and is_staff_submission(s, course):
                    continue

                archive_dirname = '_'.join(
                    sorted(s.submission_group.member_names)) + '-' + s.timestamp.isoformat()
                with misc_ut.ChangeDirectory(ut.get_submission_dir(s)):
                    for filename in s.submitted_filenames:
                        target_name = os.path.join(
                            '{}_{}'.format(course.name, project.name),
                            archive_dirname, filename)
                        print(target_name)
                        z.write(filename, arcname=target_name)


def is_staff_submission(submission, course):
    for user in submission.submission_group.members.all():
        if course.is_course_staff(user):
            return True

    return False
