import os
import shutil
import time

from celery import shared_task

from autograder.models import Course, Submission

import autograder.shared.utilities as ut


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
    submission = Submission.objects.get(pk=submission_id)
    test_cases = submission.submission_group.project.autograder_test_cases.all()
    temp_dirname = 'grading_dir'
    project_files_dir = ut.get_project_files_dir(
        submission.submission_group.project)
    with ut.ChangeDirectory(ut.get_submission_dir(submission)):
        for test_case in test_cases:
            with ut.TemporaryDirectory(temp_dirname):
                student_files = submission.get_submitted_file_basenames()

                for filename in student_files:
                    shutil.copy(filename, temp_dirname)

                for filename in test_case.test_resource_files:
                    shutil.copy(
                        os.path.join(project_files_dir, filename),
                        temp_dirname)

                with ut.ChangeDirectory(temp_dirname):
                    for filename in os.listdir():
                        os.chmod(filename, 0o666)
                    result = test_case.run()
                    print(result)
                    result.save()
