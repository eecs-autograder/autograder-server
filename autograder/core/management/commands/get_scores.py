#! /usr/bin/env python3

import csv
# import traceback

from django.core.management.base import BaseCommand

from autograder.core.models import Course


class Command(BaseCommand):
    help = 'Dumps ultimate submission score breakdown to a csv file'

    def add_arguments(self, parser):
        parser.add_argument('course_name')
        parser.add_argument('project_name')
        parser.add_argument('csv_filename')

        parser.add_argument(
            '--include_staff', '-s', action='store_true', default=False)

    def handle(self, *args, **options):
        course = Course.objects.get(name=options['course_name'])
        project = course.projects.get(name=options['project_name'])

        groups = project.submission_groups.all()
        submissions = [group.ultimate_submission for group in groups if group.submissions.count()]

        row_headers = (['usernames', 'timestamp'] +
                       [test.name for test in project.autograder_test_cases.all()] +
                       ['total'])
        with open(options['csv_filename'], 'w') as f:
            writer = csv.DictWriter(f, fieldnames=row_headers)
            writer.writeheader()
            for submission in submissions:
                if not options['include_staff'] and is_staff_submission(submission, course):
                    continue
                row = {'usernames': '_'.join(submission.submission_group.member_names),
                       'timestamp': submission.timestamp}
                total = 0
                for result in submission.results.all():
                    fdbk = result.get_max_feedback()
                    row[fdbk.ag_test_name] = fdbk.total_points
                    total += fdbk.total_points

                row['total'] = total
                writer.writerow(row)


def is_staff_submission(submission, course):
    for user in submission.submission_group.members.all():
        if course.is_course_staff(user):
            return True

    return False
