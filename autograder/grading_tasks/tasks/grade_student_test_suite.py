import shutil
import traceback
import uuid
from typing import List, Tuple

import celery
from autograder_sandbox import AutograderSandbox
from autograder_sandbox.autograder_sandbox import CompletedCommand
from django.db import transaction

import autograder.core.models as ag_models
from autograder.core import constants
from .utils import (
    add_files_to_sandbox, run_command, retry_should_recover, mark_submission_as_error)


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
            setup_run_result = run_command(sandbox, student_test_suite.setup_command.to_dict())
            if setup_run_result.return_code != 0:
                _save_results(student_test_suite, submission,
                              setup_run_result, [], [], [], [], [], [])
                return
        else:
            setup_run_result = None

        get_test_names_result = run_command(
            sandbox, student_test_suite.get_student_test_names_command.to_dict())
        student_tests = (
            get_test_names_result.stdout.read().decode(errors='backslashreplace').split())

        valid_tests = []
        invalid_tests = []
        timed_out_tests = []

        validity_check_run_results = []

        for test in student_tests:
            cmd_kwargs = student_test_suite.student_test_validity_check_command.to_dict()
            concrete_cmd = cmd_kwargs['cmd'].replace(
                ag_models.StudentTestSuite.STUDENT_TEST_NAME_PLACEHOLDER, test)
            cmd_kwargs['cmd'] = concrete_cmd

            validity_run_result = run_command(sandbox, cmd_kwargs)
            validity_check_run_results.append((test, validity_run_result))

            if validity_run_result.return_code == 0:
                valid_tests.append(test)
            else:
                invalid_tests.append(test)

            if validity_run_result.timed_out:
                timed_out_tests.append(test)

        exposed_bugs = []
        buggy_impl_run_results = []

        for bug in student_test_suite.buggy_impl_names:
            for test in valid_tests:
                cmd_kwargs = student_test_suite.grade_buggy_impl_command.to_dict()
                concrete_cmd = cmd_kwargs['cmd'].replace(
                    ag_models.StudentTestSuite.STUDENT_TEST_NAME_PLACEHOLDER, test
                ).replace(ag_models.StudentTestSuite.BUGGY_IMPL_NAME_PLACEHOLDER, bug)
                print(concrete_cmd)
                cmd_kwargs['cmd'] = concrete_cmd

                buggy_impl_run_result = run_command(sandbox, cmd_kwargs)
                buggy_impl_run_results.append((test, bug, buggy_impl_run_result))

                if buggy_impl_run_result.return_code != 0:
                    exposed_bugs.append(bug)
                    break

        _save_results(student_test_suite, submission,
                      setup_run_result, validity_check_run_results,
                      buggy_impl_run_results,
                      student_tests, invalid_tests, timed_out_tests,
                      exposed_bugs)


@retry_should_recover
@transaction.atomic()
def _save_results(student_test_suite: ag_models.StudentTestSuite,
                  submission: ag_models.Submission,
                  setup_run_result: CompletedCommand,
                  validity_check_run_results: List[Tuple[str, CompletedCommand]],
                  grade_buggy_impl_run_results: List[Tuple[str, str, CompletedCommand]],
                  student_tests: List[str],
                  invalid_tests: List[str],
                  timed_out_tests: List[str],
                  bugs_exposed: List[str]):
    result_kwargs = {
        'student_tests': student_tests,
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
        shutil.move(setup_run_result.stdout.name, setup_result.stdout_filename)
        shutil.move(setup_run_result.stderr.name, setup_result.stderr_filename)

        result.setup_result = setup_result
        result.save()

    with result.open_validity_check_stdout('wb') as stdout, \
            result.open_validity_check_stderr('wb') as stderr:
        for test, validity_result in validity_check_run_results:
            line = '\n------ {} ------\n'.format(test).encode()
            stdout.write(line)
            stdout.write(validity_result.stdout.read())

            stderr.write(line)
            stderr.write(validity_result.stderr.read())

    with result.open_grade_buggy_impls_stdout('wb') as stdout, \
            result.open_grade_buggy_impls_stderr('wb') as stderr:
        for test, bug, grade_impl_result in grade_buggy_impl_run_results:
            line = '\n------ Bug "{}" with Test "{}" ------\n'.format(bug, test).encode()

            stdout.write(line)
            stdout.write(grade_impl_result.stdout.read())

            stderr.write(line)
            stderr.write(grade_impl_result.stderr.read())
