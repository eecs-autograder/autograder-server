import gzip
import json
import os
from pathlib import Path
import shutil

from autograder.core.constants import COMPRESSED_OUTPUT_SUFFIX
import autograder.core.models as ag_models
from autograder.core.submission_feedback import AGTestCommandResultFeedback, AGTestPreLoader
from autograder.core.utils import get_diff_size


def migrate_ag_test_suite_result_output(ag_test_suite_result: ag_models.AGTestSuiteResult):
    if (ag_test_suite_result.setup_stdout_size is not None
            and ag_test_suite_result.setup_stderr_size is not None):
        return

    if ag_test_suite_result.has_setup_result:
        _compress_output_file(ag_test_suite_result.setup_stdout_filename)
        _compress_output_file(ag_test_suite_result.setup_stderr_filename)

        stdout_size = os.path.getsize(ag_test_suite_result.setup_stdout_filename)
        stderr_size = os.path.getsize(ag_test_suite_result.setup_stderr_filename)

        ag_test_suite_result.setup_stdout_size = stdout_size
        ag_test_suite_result.setup_stderr_size = stderr_size
    else:
        ag_test_suite_result.setup_stdout_size = 0
        ag_test_suite_result.setup_stderr_size = 0

    ag_test_suite_result.save()


def migrate_ag_test_command_result_output(ag_test_command_result: ag_models.AGTestCommandResult):
    if (ag_test_command_result.stdout_size is not None
            and ag_test_command_result.stderr_size is not None
            and ag_test_command_result.stdout_diff_size is not None
            and ag_test_command_result.stderr_diff_size is not None):
        return

    _compress_output_file(ag_test_command_result.stdout_filename)
    _compress_output_file(ag_test_command_result.stderr_filename)

    stdout_size = os.path.getsize(ag_test_command_result.stdout_filename)
    stderr_size = os.path.getsize(ag_test_command_result.stderr_filename)

    fdbk = AGTestCommandResultFeedback(
        ag_test_command_result,
        ag_models.FeedbackCategory.max,
        AGTestPreLoader(
            ag_test_command_result.ag_test_case_result
            .ag_test_suite_result.submission.project
        ),
    )

    stdout_diff = fdbk.stdout_diff
    stdout_diff_size = None
    stderr_diff = fdbk.stderr_diff
    stderr_diff_size = None

    if stdout_diff is not None:
        stdout_diff_size = get_diff_size(stdout_diff.diff_content)
        with gzip.open(ag_test_command_result.stdout_diff_filename, 'wt') as f:
            json.dump(stdout_diff.to_dict(), f)

    if stderr_diff is not None:
        stderr_diff_size = get_diff_size(stderr_diff.diff_content)
        with gzip.open(ag_test_command_result.stderr_diff_filename, 'wt') as f:
            json.dump(stderr_diff.to_dict(), f)

    ag_test_command_result.stdout_size = stdout_size
    ag_test_command_result.stderr_size = stderr_size
    ag_test_command_result.stdout_diff_size = stdout_diff_size
    ag_test_command_result.stderr_diff_size = stderr_diff_size
    ag_test_command_result.save()


def migrate_mutation_test_suite_result_output(
    mutation_test_suite_result: ag_models.MutationTestSuiteResult
):
    if (
        mutation_test_suite_result.setup_stdout_size is not None
        and mutation_test_suite_result.setup_stderr_size is not None
        and mutation_test_suite_result.get_student_test_names_stdout_size is not None
        and mutation_test_suite_result.get_student_test_names_stderr_size is not None
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

    if mutation_test_suite_result.setup_result is not None:
        mutation_test_suite_result.setup_stdout_size = os.path.getsize(
            mutation_test_suite_result.old_setup_stdout_filename)
        mutation_test_suite_result.setup_stderr_size = os.path.getsize(
            mutation_test_suite_result.old_setup_stderr_filename)

    mutation_test_suite_result.get_student_test_names_stdout_size = os.path.getsize(
        mutation_test_suite_result.old_get_test_names_stdout_filename)
    mutation_test_suite_result.get_student_test_names_stderr_size = os.path.getsize(
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

    Path(new_filename).parent.mkdir(parents=True, exist_ok=True)

    with (open(output_filename, 'rb') as from_file,
            gzip.open(new_filename, 'wb') as to_file):
        shutil.copyfileobj(from_file, to_file)
