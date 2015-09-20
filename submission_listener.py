#! /usr/bin/env python3

import os
import sys
sys.path.append(os.path.basename(os.path.abspath(__file__)))
import traceback
import time
import uuid
import datetime

# HACK: Need to be able to specify whether to use the main settings
# file or the system test one.
if len(sys.argv) != 2:
    print('Usage: {} settings_module')

os.environ.setdefault("DJANGO_SETTINGS_MODULE", sys.argv[1])

import django
django.setup()
from django.db import transaction

# import autograder.models

from autograder.models import Submission
from autograder.autograder_sandbox import AutograderSandbox

import autograder.shared.utilities as ut


DIVIDER = '=' * 79 + '\n'


def main():
    print(os.getpid())
    print('hello world')

    while True:
        to_grade = None
        submission_id = None
        with transaction.atomic():
            queued = Submission.objects.select_for_update().filter(
                status='queued').order_by('_timestamp')
            if not queued:
                time.sleep(1)
                continue
            to_grade = queued[0]
            submission_id = to_grade.pk
            print(to_grade.submission_group.members)
            to_grade.status = 'being_graded'
            to_grade.save()
            print('saved')

        print('going to grade')
        grade_submission(submission_id)
        print(DIVIDER * 3)
        to_grade = None
        submission_id = None


def grade_submission(submission_id):
    print('grade_submission')
    try:
        submission = Submission.objects.get(pk=submission_id)
        submission.status = Submission.GradingStatus.being_graded
        submission.save()

        with ut.ChangeDirectory(ut.get_submission_dir(submission)):
            _prepare_and_run_tests(submission)
            submission.status = Submission.GradingStatus.finished_grading
            submission.save()
    except Exception as e:
        print(e)
        traceback.print_exc()
        submission.status = Submission.GradingStatus.error
        submission.invalid_reason_or_error = [str(e)]
        submission.save()


def _prepare_and_run_tests(submission):
    group = submission.submission_group
    project_files_dir = ut.get_project_files_dir(group.project)

    sandbox_name = '{}-{}-{}'.format(
        '_'.join(sorted(group.members)).replace('@', '.'),
        submission.timestamp.strftime('%Y-%m-%d_%H.%M.%S'),
        uuid.uuid4().hex)
    print(sandbox_name)

    with AutograderSandbox(name=sandbox_name) as sandbox:
        for test_case in group.project.autograder_test_cases.all():
            print(test_case.name)
            files_to_copy = (
                test_case.student_resource_files +
                [os.path.join(project_files_dir, filename) for
                 filename in test_case.test_resource_files])
            sandbox.copy_into_sandbox(*files_to_copy)

            result = test_case.run(
                submission=submission, autograder_sandbox=sandbox)
            print('finished_running')
            result.save()

            sandbox.clear_working_dir()

if __name__ == '__main__':
    try:
        main()
    except KeyboardInterrupt:
        print('KEYBOARD INTERRUPT. Shutting down...')
    except Exception as e:
        print('SOMETHING VERY BAD HAPPENED')
        print(e)
        traceback.print_exc()
