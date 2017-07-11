import itertools

import sys
import os
import django
from django.db import transaction

sys.path.append('.')
# os.environ.setdefault("DJANGO_SETTINGS_MODULE", "autograder.settings.production")
django.setup()

from autograder.core.models import *
from autograder.core.models.autograder_test_case import feedback_config


def main():
    convert_ag_tests()
    print('done')


def convert_ag_tests():
    for p in Project.objects.all():
        print(p.name)
        print(p.pk)
        if p.ag_test_suites.count():
            print('already converted, skipping...')
            continue
        with transaction.atomic():
            for old_test in p.autograder_test_cases.all():
                print(old_test.name)
                setup_cmd = ''
                points_for_correct_return_code = old_test.points_for_correct_return_code
                if isinstance(old_test, CompiledAndRunAutograderTestCase):
                    setup_cmd = ' '.join(
                        [old_test.compiler] +
                        list(itertools.chain(
                            (file_.name for file_ in old_test.project_files_to_compile_together.all()),
                            (pattern.pattern for pattern in old_test.student_files_to_compile_together.all()))) +
                        old_test.compiler_flags)
                elif isinstance(old_test, CompilationOnlyAutograderTestCase):
                    cmd = ' '.join(
                        [old_test.compiler] +
                        list(itertools.chain(
                            (file_.name for file_ in old_test.project_files_to_compile_together.all()),
                            (pattern.pattern for pattern in old_test.student_files_to_compile_together.all()))) +
                        old_test.compiler_flags)
                    points_for_correct_return_code = old_test.points_for_compilation_success

                new_suite = AGTestSuite.objects.validate_and_create(
                    name=old_test.name,
                    project=p,
                    project_files_needed=list(itertools.chain(
                        old_test.test_resource_files.all(),
                        old_test.project_files_to_compile_together.all())),
                    student_files_needed=list(itertools.chain(
                        old_test.student_resource_files.all(),
                        old_test.student_files_to_compile_together.all()
                    )),
                    setup_suite_cmd=setup_cmd,
                    allow_network_access=old_test.allow_network_connections,
                    deferred=old_test.deferred
                )
                new_case = AGTestCase.objects.validate_and_create(name=new_suite.name,
                                                                  ag_test_suite=new_suite)
                if isinstance(old_test, CompiledAndRunAutograderTestCase):
                    cmd = './{} {}'.format(old_test.executable_name, ' '.join(
                        old_test.command_line_arguments))
                elif isinstance(old_test, InterpretedAutograderTestCase):
                    cmd = '{} {} {} {}'.format(old_test.interpreter,
                                               ' '.join(old_test.interpreter_flags),
                                               old_test.entry_point_filename,
                                               ' '.join(old_test.command_line_arguments))

                expected_return_code = ExpectedReturnCode.none
                if old_test.expect_any_nonzero_return_code:
                    expected_return_code = ExpectedReturnCode.nonzero
                elif old_test.expected_return_code == 0:
                    expected_return_code = ExpectedReturnCode.zero
                elif isinstance(old_test, CompilationOnlyAutograderTestCase):
                    expected_return_code = ExpectedReturnCode.zero

                expected_stdout = ''
                expected_stdout_source = ExpectedOutputSource.none
                if old_test.expected_standard_output:
                    expected_stdout = old_test.expected_standard_output
                    expected_stdout_source = ExpectedOutputSource.text

                expected_stderr = ''
                expected_stderr_source = ExpectedOutputSource.none
                if old_test.expected_standard_error_output:
                    expected_stderr = old_test.expected_standard_error_output
                    expected_stderr_source = ExpectedOutputSource.text

                new_cmd = AGTestCommand.objects.validate_and_create(
                    name=new_suite.name,
                    ag_test_case=new_case,
                    cmd=cmd,

                    stdin_source=StdinSource.text,
                    stdin_text=old_test.standard_input,

                    expected_return_code=expected_return_code,

                    expected_stdout_source=expected_stdout_source,
                    expected_stdout_text=expected_stdout,
                    expected_stderr_source=expected_stderr_source,
                    expected_stderr_text=expected_stderr,

                    ignore_case=old_test.ignore_case,
                    ignore_whitespace=old_test.ignore_whitespace,
                    ignore_whitespace_changes=old_test.ignore_whitespace_changes,
                    ignore_blank_lines=old_test.ignore_blank_lines,

                    points_for_correct_return_code=points_for_correct_return_code,
                    points_for_correct_stdout=old_test.points_for_correct_stdout,
                    points_for_correct_stderr=old_test.points_for_correct_stderr,

                    normal_fdbk_config={
                        'visible': old_test.visible_to_students,
                        'return_code_fdbk_level': convert_return_code_fdbk(
                            old_test.feedback_configuration.return_code_fdbk),
                        'stdout_fdbk_level': convert_output_fdbk(
                            old_test.feedback_configuration.stdout_fdbk),
                        'stderr_fdbk_level': convert_output_fdbk(
                            old_test.feedback_configuration.stderr_fdbk),
                        'show_points': old_test.feedback_configuration.points_fdbk == 'show_breakdown',
                        'show_actual_return_code': old_test.feedback_configuration.show_return_code,
                        'show_actual_stdout': old_test.feedback_configuration.show_stdout_content,
                        'show_actual_stderr': old_test.feedback_configuration.show_stderr_content,
                        'show_whether_timed_out': True
                    },
                    ultimate_submission_fdbk_config={
                        'visible': old_test.visible_in_ultimate_submission,
                        'return_code_fdbk_level': convert_return_code_fdbk(
                            old_test.ultimate_submission_fdbk_conf.return_code_fdbk),
                        'stdout_fdbk_level': convert_output_fdbk(
                            old_test.ultimate_submission_fdbk_conf.stdout_fdbk),
                        'stderr_fdbk_level': convert_output_fdbk(
                            old_test.ultimate_submission_fdbk_conf.stderr_fdbk),
                        'show_points': old_test.ultimate_submission_fdbk_conf.points_fdbk == 'show_breakdown',
                        'show_actual_return_code': old_test.ultimate_submission_fdbk_conf.show_return_code,
                        'show_actual_stdout': old_test.ultimate_submission_fdbk_conf.show_stdout_content,
                        'show_actual_stderr': old_test.ultimate_submission_fdbk_conf.show_stderr_content,
                        'show_whether_timed_out': True
                    },
                    past_limit_submission_fdbk_config={
                        'visible': old_test.visible_in_past_limit_submission,
                        'return_code_fdbk_level': convert_return_code_fdbk(
                            old_test.past_submission_limit_fdbk_conf.return_code_fdbk),
                        'stdout_fdbk_level': convert_output_fdbk(
                            old_test.past_submission_limit_fdbk_conf.stdout_fdbk),
                        'stderr_fdbk_level': convert_output_fdbk(
                            old_test.past_submission_limit_fdbk_conf.stderr_fdbk),
                        'show_points': old_test.past_submission_limit_fdbk_conf.points_fdbk == 'show_breakdown',
                        'show_actual_return_code': old_test.past_submission_limit_fdbk_conf.show_return_code,
                        'show_actual_stdout': old_test.past_submission_limit_fdbk_conf.show_stdout_content,
                        'show_actual_stderr': old_test.past_submission_limit_fdbk_conf.show_stderr_content,
                        'show_whether_timed_out': False
                    },
                    staff_viewer_fdbk_config={
                        'visible': True,
                        'return_code_fdbk_level': convert_return_code_fdbk(
                            old_test.staff_viewer_fdbk_conf.return_code_fdbk),
                        'stdout_fdbk_level': convert_output_fdbk(
                            old_test.staff_viewer_fdbk_conf.stdout_fdbk),
                        'stderr_fdbk_level': convert_output_fdbk(
                            old_test.staff_viewer_fdbk_conf.stderr_fdbk),
                        'show_points': old_test.staff_viewer_fdbk_conf.points_fdbk == 'show_breakdown',
                        'show_actual_return_code': old_test.staff_viewer_fdbk_conf.show_return_code,
                        'show_actual_stdout': old_test.staff_viewer_fdbk_conf.show_stdout_content,
                        'show_actual_stderr': old_test.staff_viewer_fdbk_conf.show_stderr_content,
                        'show_whether_timed_out': True
                    },

                    time_limit=old_test.time_limit,
                    stack_size_limit=old_test.stack_size_limit,
                    virtual_memory_limit=old_test.virtual_memory_limit,
                    process_spawn_limit=old_test.process_spawn_limit,
                )

                if old_test.use_valgrind:
                    valgrind_cmd = AGTestCommand.objects.validate_and_create(
                        name='Valgrind',
                        ag_test_case=new_case,
                        cmd='valgrind {} {}'.format(' '.join(old_test.valgrind_flags), new_cmd.cmd),
                        stdin_source=StdinSource.text,
                        stdin_text=old_test.standard_input,
                        expected_return_code=ExpectedReturnCode.zero,
                        deduction_for_wrong_return_code=-old_test.deduction_for_valgrind_errors,

                        time_limit=old_test.time_limit,
                        stack_size_limit=old_test.stack_size_limit,
                        virtual_memory_limit=old_test.virtual_memory_limit,
                        process_spawn_limit=old_test.process_spawn_limit,
                    )

                convert_results(project, old_test, new_case)


def convert_results(project, old_test: AutograderTestCaseBase, new_test_case: AGTestCase):
    new_suite = new_test_case.ag_test_suite
    for result in old_test.dependent_results.all():
        setup_stdout = ''
        setup_stderr = ''
        setup_return_code = None
        if isinstance(old_test, CompiledAndRunAutograderTestCase):
            setup_stdout = result.compilation_standard_output
            setup_stderr = result.compilation_standard_error_output
            setup_return_code = result.compilation_return_code

        suite_result = AGTestSuiteResult.objects.validate_and_create(
            ag_test_suite=new_suite,
            submission=result.submission,
            setup_stdout=setup_stdout,
            setup_stderr=setup_stderr,
            setup_return_code=setup_return_code,
        )

        case_result = AGTestCaseResult.objects.validate_and_create(
            ag_test_case=new_test_case,
            ag_test_suite_result=suite_result
        )

        stdout_correct = None
        stderr_correct = None
        if isinstance(old_test, CompilationOnlyAutograderTestCase):
            stdout = result.compilation_standard_output
            stderr = result.compilation_standard_error_output
            return_code = result.compilation_return_code
            return_code_correct = result.get_max_feedback().compilation_succeeded
            timed_out = False
        else:
            stdout = result.standard_output
            stderr = result.standard_error_output
            return_code = result.return_code
            return_code_correct = result.get_max_feedback().return_code_correct
            stdout_correct = result.get_max_feedback().stdout_correct
            stderr_correct = result.get_max_feedback().stderr_correct
            timed_out = result.timed_out

        cmd_result = AGTestCommandResult.objects.validate_and_create(
            ag_test_command=new_test_case.ag_test_commands.first(),
            ag_test_case_result=case_result,
            stdout=stdout,
            stderr=stderr,
            return_code=return_code,
            return_code_correct=return_code_correct,
            stdout_correct=stdout_correct,
            stderr_correct=stderr_correct,
            timed_out=timed_out,
        )

        if old_test.use_valgrind:
            valgrind_cmd_result = AGTestCommandResult.objects.validate_and_create(
                ag_test_command=new_test_case.ag_test_commands.all()[1],
                ag_test_case_result=case_result,
                stderr=result.valgrind_output,
                return_code=result.return_code,
                return_code_correct=result.valgrind_return_code == 0,
                timed_out=timed_out
            )


def convert_return_code_fdbk(old_fdbk):
    if old_fdbk == feedback_config.ReturnCodeFdbkLevel.no_feedback:
        return ValueFeedbackLevel.no_feedback
    elif old_fdbk == feedback_config.ReturnCodeFdbkLevel.correct_or_incorrect_only:
        return ValueFeedbackLevel.correct_or_incorrect
    elif old_fdbk == feedback_config.ReturnCodeFdbkLevel.show_expected_and_actual_values:
        return ValueFeedbackLevel.expected_and_actual


def convert_output_fdbk(old_fdbk):
    if old_fdbk == 'no_feedback':
        return ValueFeedbackLevel.no_feedback
    if old_fdbk == 'correct_or_incorrect_only':
        return ValueFeedbackLevel.correct_or_incorrect
    if old_fdbk == 'show_expected_and_actual_values':
        return ValueFeedbackLevel.expected_and_actual

#
# def revert_ag_tests():
#     for p in Project.objects.all():
#         p.ag_test_suites.all().delete()


if __name__ == '__main__':
    main()
