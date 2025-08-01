import gzip
import os
import shutil

from django.db import transaction

from autograder.core.constants import COMPRESSED_OUTPUT_SUFFIX
import autograder.core.models as ag_models


def migrate_ag_test_suite_result_output(ag_test_suite_result: ag_models.AGTestSuiteResult):
    if (ag_test_suite_result.setup_stdout_size is not None
            and ag_test_suite_result.setup_stderr_size is not None):
        return

    _compress_output_file(ag_test_suite_result.setup_stdout_filename)
    _compress_output_file(ag_test_suite_result.setup_stderr_filename)

    stdout_size = os.path.getsize(ag_test_suite_result.setup_stdout_filename)
    stderr_size = os.path.getsize(ag_test_suite_result.setup_stderr_filename)

    with transaction.atomic():
        ag_test_suite_result.setup_stdout_size = stdout_size
        ag_test_suite_result.setup_stderr_size = stderr_size
        ag_test_suite_result.save()


def migrate_ag_test_command_result_output(ag_test_command_result: ag_models.AGTestCommandResult):
    if (ag_test_command_result.stdout_size is not None
            and ag_test_command_result.stderr_size is not None):
        return

    _compress_output_file(ag_test_command_result.stdout_filename)
    _compress_output_file(ag_test_command_result.stderr_filename)

    stdout_size = os.path.getsize(ag_test_command_result.stdout_filename)
    stderr_size = os.path.getsize(ag_test_command_result.stderr_filename)

    with transaction.atomic():
        ag_test_command_result.stdout_size = stdout_size
        ag_test_command_result.stderr_size = stderr_size
        ag_test_command_result.save()


def migrate_mutation_test_suite_result_output(
    mutation_test_suite_result: ag_models.MutationTestSuiteResult
):
    if (
        mutation_test_suite_result.setup_stdout_size is not None
        and mutation_test_suite_result.setup_stderr_size is not None
        and mutation_test_suite_result.student_test_names_stdout_size is not None
        and mutation_test_suite_result.student_test_names_stderr_size is not None
        and mutation_test_suite_result.validity_check_stdout_size is not None
        and mutation_test_suite_result.validity_check_stderr_size is not None
        and mutation_test_suite_result.grade_buggy_impls_stdout_size is not None
        and mutation_test_suite_result.grade_buggy_impls_stderr_size is not None
    ):
        return

    if mutation_test_suite_result.setup_result is not None:
        _compress_output_file(
            mutation_test_suite_result.old_setup_stdout_filename,
            mutation_test_suite_result.setup_stdout_filename,
        )
        _compress_output_file(
            mutation_test_suite_result.old_setup_stderr_filename,
            mutation_test_suite_result.setup_stderr_filename,
        )

    _compress_output_file(
        mutation_test_suite_result.old_get_test_names_stdout_filename,
        mutation_test_suite_result.get_test_names_stdout_filename,
    )
    _compress_output_file(
        mutation_test_suite_result.old_get_test_names_stderr_filename,
        mutation_test_suite_result.get_test_names_stderr_filename,
    )
    _compress_output_file(mutation_test_suite_result.validity_check_stdout_filename)
    _compress_output_file(mutation_test_suite_result.validity_check_stderr_filename)
    _compress_output_file(mutation_test_suite_result.grade_buggy_impls_stdout_filename)
    _compress_output_file(mutation_test_suite_result.grade_buggy_impls_stderr_filename)

    with transaction.atomic():
        if mutation_test_suite_result.setup_result is not None:
            mutation_test_suite_result.setup_stdout_size = os.path.getsize(
                mutation_test_suite_result.old_setup_stdout_filename)
            mutation_test_suite_result.setup_stderr_size = os.path.getsize(
                mutation_test_suite_result.old_setup_stderr_filename)

        mutation_test_suite_result.student_test_names_stdout_size = os.path.getsize(
            mutation_test_suite_result.old_get_test_names_stdout_filename)
        mutation_test_suite_result.student_test_names_stderr_size = os.path.getsize(
            mutation_test_suite_result.old_get_test_names_stderr_filename)

        mutation_test_suite_result.validity_check_stdout_size = os.path.getsize(
            mutation_test_suite_result.validity_check_stdout_filename)
        mutation_test_suite_result.validity_check_stderr_size = os.path.getsize(
            mutation_test_suite_result.validity_check_stderr_filename)

        mutation_test_suite_result.grade_buggy_impls_stdout_size = os.path.getsize(
            mutation_test_suite_result.grade_buggy_impls_stdout_filename)

        mutation_test_suite_result.grade_buggy_impls_stderr_size = os.path.getsize(
            mutation_test_suite_result.grade_buggy_impls_stderr_filename)
        mutation_test_suite_result.save()


def _compress_output_file(output_filename: str, new_filename: str | None = None):
    if os.path.getsize(output_filename) == 0:
        return

    # If new_filename is provided, it should have
    # COMPRESSED_OUTPUT_SUFFIX already appended
    if new_filename is None:
        new_filename = output_filename + COMPRESSED_OUTPUT_SUFFIX

    with (open(output_filename, 'rb') as from_file,
            gzip.open(new_filename, 'wb') as to_file):
        shutil.copyfileobj(from_file, to_file)
