# import os
# import time
# from celery import shared_task

# from autograder.models import Course, Submission
# from autograder.autograder_sandbox import AutograderSandbox

# import autograder.shared.utilities as ut

# import logging
# logger = logging.getLogger(__name__)


# @shared_task(bind=True, ignore_result=True)
# def debug_task(self):
#     print('starting task')
#     for i in range(5):
#         courses = Course.objects.all()
#         print(courses)
#         if courses:
#             print('found {} courses'.format(courses.count()))
#         else:
#             print('no courses found')
#         print('Waiting for {} seconds'.format(i))
#         time.sleep(i)
#     print('all done')


# @shared_task(bind=True, ignore_result=True)
# def grade_submission(self, submission_id):
#     try:
#         submission = Submission.objects.get(pk=submission_id)
#         submission.status = Submission.GradingStatus.being_graded
#         submission.save()

#         with ut.ChangeDirectory(ut.get_submission_dir(submission)):
#             _prepare_and_run_tests(submission)
#             submission.status = Submission.GradingStatus.finished_grading
#             submission.save()
#     except Exception as e:
#         submission.status = Submission.GradingStatus.error
#         submission.invalid_reason_or_error = [str(e)]
#         submission.save()


# def _prepare_and_run_tests(submission):
#     group = submission.submission_group
#     project_files_dir = ut.get_project_files_dir(group.project)

#     sandbox_name = '{}-{}'.format(
#         '_'.join(sorted(group.members)).replace('@', '.'),
#         submission.timestamp.strftime('%Y-%m-%d_%H.%M.%S'))
#     print(sandbox_name)

#     with AutograderSandbox(name=sandbox_name) as sandbox:
#         for test_case in group.project.autograder_test_cases.all():
#             print(test_case.name)
#             files_to_copy = (
#                 test_case.student_resource_files +
#                 [os.path.join(project_files_dir, filename) for
#                  filename in test_case.test_resource_files])
#             sandbox.copy_into_sandbox(*files_to_copy)

#             result = test_case.run(
#                 submission=submission, autograder_sandbox=sandbox)
#             print('finished_running')
#             result.save()

#             sandbox.clear_working_dir()
