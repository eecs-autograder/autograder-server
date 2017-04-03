import os
import tempfile
import subprocess

from django.conf import settings
from django.core import exceptions
from django.utils import timezone

from . import constants as const


def get_diff(first, second,
             ignore_case=False,
             ignore_whitespace=False,
             ignore_whitespace_changes=False,
             ignore_blank_lines=False):
    '''
    Diffs first and second using the GNU diff command line utility.
    Returns an empty list if first and second are considered equivalent.
    Otherwise, returns a list of strings, each of which are prefixed
    with one of the two-letter opcodes used by
    https://docs.python.org/3.5/library/difflib.html#difflib.Differ
    '''
    with tempfile.NamedTemporaryFile('w') as f1, tempfile.NamedTemporaryFile('w') as f2:
        f1.write(first)
        f1.seek(0)
        f2.write(second)
        f2.seek(0)

        diff_cmd = ['diff',
                    '--new-line-format', '+ %L',
                    '--old-line-format', '- %L',
                    '--unchanged-line-format', '  %L']
        if ignore_case:
            diff_cmd.append('--ignore-case')
        if ignore_whitespace:
            diff_cmd.append('--ignore-all-space')
        if ignore_whitespace_changes:
            diff_cmd.append('--ignore-space-change')
        if ignore_blank_lines:
            diff_cmd.append('--ignore-blank-lines')

        diff_cmd += [f1.name, f2.name]

        diff_result = subprocess.run(
            diff_cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
        if diff_result.returncode == 0:
            return list()

        return diff_result.stdout.decode(
            'utf-8', 'backslashreplace').splitlines(keepends=True)


def get_24_hour_period(start_time, contains_datetime):
    '''
    Returns a tuple (start_datetime, end_datetime) representing a 24
    hour period that contains the current date and time and with the
    start and end time both being start_time.
    '''
    start_date = contains_datetime.date()
    if contains_datetime.time() < start_time:
        start_date += timezone.timedelta(days=-1)

    start_datetime = timezone.datetime.combine(
        start_date, start_time)
    start_datetime = start_datetime.replace(
        tzinfo=contains_datetime.tzinfo)
    end_datetime = start_datetime + timezone.timedelta(days=1)

    return start_datetime, end_datetime


def check_user_provided_filename(filename, allow_empty=False):
    """
    Verifies whether the given filename is valid according to the
    following requirements:
        - Filenames must be non-empty and non-null
        - Filenames must only contain the characters specified in
          autograder.shared.global_constants.PROJECT_FILENAME_WHITELIST_REGEX
        - Filenames must start with an alphabetic character.

    If the given filename does not meet these requirements, ValidationError
    is raised. These restrictions are placed on filenames for security
    purposes.
    """
    if filename is None:
        raise exceptions.ValidationError("Filenames must be non-null")

    if not filename and not allow_empty:
        raise exceptions.ValidationError("Filenames must be non-empty")

    if not const.PROJECT_FILENAME_WHITELIST_REGEX.fullmatch(filename):
        raise exceptions.ValidationError(
            "Invalid filename: {0} \n"
            "Filenames must contain only alphanumeric characters, hyphen, "
            "underscore, and period.".format(filename))


def check_shell_style_file_pattern(pattern):
    """
    Verified whether the given file pattern is valid according to the
    following requirements:
        - Patterns must be non-empty and non-null
        - Filenames myst only contain characters specified in
          autograder.shared.global_constants.PROJECT_FILE_PATTERN_WHITELIST_REGEX

    If the given pattern does not meet these requirements, ValidationError
    is raised. These restrictions are placed on file patterns for security
    purposes.
    """
    if not pattern:
        raise exceptions.ValidationError("File patterns must be non-empty")

    if not const.PROJECT_FILE_PATTERN_WHITELIST_REGEX.fullmatch(pattern):
        raise exceptions.ValidationError(
            "Invalid file pattern: {0} \n"
            "Shell-style patterns must only contain "
            "alphanumeric characters, hyphen, underscore, "
            "period, * ? [ ] and !".format(pattern))

# -----------------------------------------------------------------------------


def get_course_root_dir(course):
    """
    Computes the absolute path of the base directory for the given course.
    """
    return os.path.join(
        settings.MEDIA_ROOT, get_course_relative_root_dir(course))


def get_course_relative_root_dir(course):
    """
    Same as get_course_root_dir() but returns a path that is
    relative to MEDIA_ROOT.
    """
    return os.path.join('courses', 'course{}'.format(course.pk))


def get_project_root_dir(project):
    """
    Computes the absolute path of the base directory for the given project.
    """
    return os.path.join(
        settings.MEDIA_ROOT, get_project_relative_root_dir(project))


def get_project_relative_root_dir(project):
    """
    Same as get_project_root_dir() but returns a path that is
    relative to MEDIA_ROOT.
    """
    return os.path.join(
        get_course_relative_root_dir(project.course),
        'project{}'.format(project.pk))


def get_project_files_dir(project):
    """
    Computes the absolute path of the directory where uploaded files
    should be stored for the given project.
    """
    return os.path.join(
        settings.MEDIA_ROOT, get_project_files_relative_dir(project))


def get_project_files_relative_dir(project):
    """
    Same as get_project_files_dir() but returns a path that is
    relative to MEDIA_ROOT.
    """
    return os.path.join(
        get_project_relative_root_dir(project), const.PROJECT_FILES_DIRNAME)


def get_project_submission_groups_dir(project):
    """
    Computes the absolute path of the directory where student submission
    groups should be stored for the given project.
    """
    return os.path.join(
        settings.MEDIA_ROOT,
        get_project_submission_groups_relative_dir(project))


def get_project_submission_groups_relative_dir(project):
    """
    Same as get_project_submission_groups_dir() but returns a path
    that is relative to MEDIA_ROOT.
    """
    return os.path.join(
        get_project_relative_root_dir(project),
        const.PROJECT_SUBMISSIONS_DIRNAME)


def get_student_submission_group_dir(submission_group):
    """
    Computes the absolute path of the directory where submissions for the
    given group should be stored.
    """
    return os.path.join(
        settings.MEDIA_ROOT,
        get_student_submission_group_relative_dir(submission_group))


def get_student_submission_group_relative_dir(submission_group):
    """
    Same as get_student_submission_group_dir() but returns a path that is
    relative to MEDIA_ROOT.
    """
    return os.path.join(
        get_project_submission_groups_relative_dir(submission_group.project),
        'group{}'.format(submission_group.pk))


def get_submission_dir(submission):
    """
    Computes the absolute path of the directory where files included
    in the given submission should be stored.
    """
    return os.path.join(
        settings.MEDIA_ROOT,
        get_submission_relative_dir(submission))


def get_submission_relative_dir(submission):
    """
    Same as get_submission_dir() but returns a path that is relative to
    MEDIA_ROOT.
    """
    return os.path.join(
        get_student_submission_group_relative_dir(submission.submission_group),
        'submission{}'.format(submission.pk))
