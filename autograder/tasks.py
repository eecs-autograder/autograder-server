import os
import shutil
import time

from celery import shared_task

from autograder.models import Course, Submission

import autograder.shared.utilities as ut

import logging
logger = logging.getLogger(__name__)

@shared_task(bind=True, ignore_result=True)
def debug_task(self):
    print('starting task')
    for i in range(5):
        courses = Course.objects.all()
        print(courses)
        if courses:
            print('found {} courses'.format(courses.count()))
        else:
            print('no courses found')
        print('Waiting for {} seconds'.format(i))
        time.sleep(i)
    print('all done')


@shared_task(bind=True, ignore_result=True)
def grade_submission(self, submission_id):
    try:
        submission = Submission.objects.get(pk=submission_id)
        submission.status = Submission.GradingStatus.being_graded
        submission.save()

        with ut.ChangeDirectory(ut.get_submission_dir(submission)):
            _prepare_and_run_tests(submission)
            submission.status = Submission.GradingStatus.finished_grading
            submission.save()
    except Exception as e:
        submission.status = Submission.GradingStatus.error
        submission.invalid_reason_or_error = [str(e)]


def _prepare_and_run_tests(submission):
    temp_dirname = 'grading_dir'
    test_cases = (
        submission.submission_group.project.autograder_test_cases.all())

    project_files_dir = ut.get_project_files_dir(
        submission.submission_group.project)

    for test_case in test_cases:
        print(test_case.name)
        with ut.TemporaryDirectory(temp_dirname):
            for filename in test_case.student_resource_files:
                shutil.copy(filename, temp_dirname)

            for filename in test_case.test_resource_files:
                shutil.copy(
                    os.path.join(project_files_dir, filename),
                    temp_dirname)

            with ut.ChangeDirectory(temp_dirname):
                for filename in os.listdir():
                    print(filename)
                    os.chmod(filename, 0o666)
                result = test_case.run(submission)
                print('finished running')
                result.save()
    print('done')
