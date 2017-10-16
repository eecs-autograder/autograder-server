import shutil
import tempfile
import traceback
import uuid
from io import FileIO
from typing import List

import celery
from autograder_sandbox import AutograderSandbox
from autograder_sandbox.autograder_sandbox import CompletedCommand
from django.db import transaction

import autograder.core.models as ag_models
from autograder.core import constants
from .utils import (
    add_files_to_sandbox, retry_should_recover, mark_submission_as_error,
    run_ag_command)


@celery.shared_task(queue='deferred', max_retries=1, acks_late=True)
def grade_deferred_student_test_suite(student_test_suite_pk, submission_pk):

    @retry_should_recover
    def _grade_deferred_student_test_suite_impl():
        grade_student_test_suite_impl(
            ag_models.StudentTestSuite.objects.get(pk=student_test_suite_pk),
            ag_models.Submission.objects.get(pk=submission_pk))

    try:
        _grade_deferred_student_test_suite_impl()
    except Exception:
        print('Error grading deferred student test suite')
        traceback.print_exc()
        mark_submission_as_error(submission_pk, traceback.format_exc())


def grade_student_test_suite_impl(student_test_suite: ag_models.StudentTestSuite,
                                  submission: ag_models.Submission):
    sandbox = AutograderSandbox(
        name='submission{}-suite{}-{}'.format(
            submission.pk, student_test_suite.pk, uuid.uuid4().hex),
        environment_variables={
            'usernames': ' '.join(sorted(submission.submission_group.member_names))
        },
        allow_network_access=student_test_suite.allow_network_access,
        docker_image=constants.DOCKER_IMAGE_IDS_TO_URLS[student_test_suite.docker_image_to_use])
    print(student_test_suite.docker_image_to_use)
    print(sandbox.docker_image)
    with sandbox:
        add_files_to_sandbox(sandbox, student_test_suite, submission)

        if student_test_suite.setup_command is not None:
            print('Running setup for', student_test_suite.name)
            setup_run_result = run_ag_command(student_test_suite.setup_command, sandbox)
            if setup_run_result.return_code != 0:
                _save_results(student_test_suite, submission, setup_run_result,
                              student_tests=[],
                              discarded_tests=[],
                              invalid_tests=[],
                              timed_out_tests=[],
                              bugs_exposed=[])
                return
        else:
            setup_run_result = None

        get_test_names_result = run_ag_command(
            student_test_suite.get_student_test_names_command, sandbox)

        if get_test_names_result.return_code != 0:
            _save_results(student_test_suite, submission, setup_run_result,
                          student_tests=[],
                          discarded_tests=[],
                          invalid_tests=[],
                          timed_out_tests=[],
                          bugs_exposed=[],
                          get_test_names_run_result=get_test_names_result)
            return

        student_tests = (
            get_test_names_result.stdout.read().decode(errors='backslashreplace').split())
        discarded_tests = []
        if len(student_tests) > student_test_suite.max_num_student_tests:
            discarded_tests = student_tests[student_test_suite.max_num_student_tests:]
            student_tests = student_tests[:student_test_suite.max_num_student_tests]

        valid_tests = []
        invalid_tests = []
        timed_out_tests = []

        validity_check_stdout = tempfile.TemporaryFile()
        validity_check_stderr = tempfile.TemporaryFile()
        for test in student_tests:
            validity_cmd = student_test_suite.student_test_validity_check_command
            concrete_cmd = validity_cmd.cmd.replace(
                ag_models.StudentTestSuite.STUDENT_TEST_NAME_PLACEHOLDER, test)

            validity_run_result = run_ag_command(validity_cmd, sandbox,
                                                 cmd_str_override=concrete_cmd)
            line = '\n------ {} ------\n'.format(test).encode()
            validity_check_stdout.write(line)
            validity_check_stderr.write(line)
            shutil.copyfileobj(validity_run_result.stdout, validity_check_stdout)
            shutil.copyfileobj(validity_run_result.stderr, validity_check_stderr)

            if validity_run_result.return_code == 0:
                valid_tests.append(test)
            else:
                invalid_tests.append(test)

            if validity_run_result.timed_out:
                timed_out_tests.append(test)

        exposed_bugs = []

        buggy_impls_stdout = tempfile.TemporaryFile()
        buggy_impls_stderr = tempfile.TemporaryFile()
        for bug in student_test_suite.buggy_impl_names:
            for valid_test in valid_tests:
                grade_cmd = student_test_suite.grade_buggy_impl_command
                concrete_cmd = grade_cmd.cmd.replace(
                    ag_models.StudentTestSuite.STUDENT_TEST_NAME_PLACEHOLDER, valid_test
                ).replace(ag_models.StudentTestSuite.BUGGY_IMPL_NAME_PLACEHOLDER, bug)

                buggy_impl_run_result = run_ag_command(grade_cmd, sandbox,
                                                       cmd_str_override=concrete_cmd)
                line = '\n----- Bug "{}" with Test "{}" -----\n'.format(bug, valid_test).encode()
                buggy_impls_stdout.write(line)
                buggy_impls_stderr.write(line)
                shutil.copyfileobj(buggy_impl_run_result.stdout, buggy_impls_stdout)
                shutil.copyfileobj(buggy_impl_run_result.stderr, buggy_impls_stderr)

                if buggy_impl_run_result.return_code != 0:
                    exposed_bugs.append(bug)
                    break

        _save_results(student_test_suite, submission,
                      setup_run_result,
                      student_tests, discarded_tests, invalid_tests, timed_out_tests, exposed_bugs,
                      get_test_names_run_result=get_test_names_result,
                      validity_check_stdout=validity_check_stdout,
                      validity_check_stderr=validity_check_stderr,
                      buggy_impls_stdout=buggy_impls_stdout,
                      buggy_impls_stderr=buggy_impls_stderr)


@retry_should_recover
@transaction.atomic()
def _save_results(student_test_suite: ag_models.StudentTestSuite,
                  submission: ag_models.Submission,
                  setup_run_result: CompletedCommand,
                  student_tests: List[str],
                  discarded_tests: List[str],
                  invalid_tests: List[str],
                  timed_out_tests: List[str],
                  bugs_exposed: List[str],
                  get_test_names_run_result: CompletedCommand=None,
                  validity_check_stdout: FileIO=None,
                  validity_check_stderr: FileIO=None,
                  buggy_impls_stdout: FileIO=None,
                  buggy_impls_stderr: FileIO=None):
    result_kwargs = {
        'student_tests': student_tests,
        'discarded_tests': discarded_tests,
        'invalid_tests': invalid_tests,
        'timed_out_tests': timed_out_tests,
        'bugs_exposed': bugs_exposed
    }
    result = ag_models.StudentTestSuiteResult.objects.update_or_create(
        defaults=result_kwargs,
        student_test_suite=student_test_suite,
        submission=submission)[0]  # type: ag_models.StudentTestSuiteResult

    if setup_run_result is not None:
        setup_result = ag_models.AGCommandResult.objects.validate_and_create(
            return_code=setup_run_result.return_code,
            timed_out=setup_run_result.timed_out,
            stdout_truncated=setup_run_result.stdout_truncated,
            stderr_truncated=setup_run_result.stderr_truncated)  # type: ag_models.AGCommandResult

        with open(setup_result.stdout_filename, 'wb') as f:
            shutil.copyfileobj(setup_run_result.stdout, f)

        with open(setup_result.stderr_filename, 'wb') as f:
            shutil.copyfileobj(setup_run_result.stdout, f)

        result.setup_result = setup_result
        result.save()

    if get_test_names_run_result is not None:
        result.get_test_names_result.return_code = get_test_names_run_result.return_code
        result.get_test_names_result.timed_out = get_test_names_run_result.timed_out
        result.get_test_names_result.save()
        with open(result.get_test_names_result.stdout_filename, 'wb') as f:
            get_test_names_run_result.stdout.seek(0)
            shutil.copyfileobj(get_test_names_run_result.stdout, f)
        with open(result.get_test_names_result.stderr_filename, 'wb') as f:
            get_test_names_run_result.stderr.seek(0)
            shutil.copyfileobj(get_test_names_run_result.stderr, f)

    if validity_check_stdout is not None:
        validity_check_stdout.seek(0)
        with open(result.validity_check_stdout_filename, 'wb') as f:
            shutil.copyfileobj(validity_check_stdout, f)
    if validity_check_stderr is not None:
        validity_check_stderr.seek(0)
        with open(result.validity_check_stderr_filename, 'wb') as f:
            shutil.copyfileobj(validity_check_stderr, f)
    if buggy_impls_stdout is not None:
        buggy_impls_stdout.seek(0)
        with open(result.grade_buggy_impls_stdout_filename, 'wb') as f:
            shutil.copyfileobj(buggy_impls_stdout, f)
    if buggy_impls_stderr is not None:
        buggy_impls_stderr.seek(0)
        with open(result.grade_buggy_impls_stderr_filename, 'wb') as f:
            shutil.copyfileobj(buggy_impls_stderr, f)
