import os
import shutil
import re

from django.conf import settings
from django.core.exceptions import ValidationError
from django.utils import timezone

import autograder.core.shared.global_constants as gc


def count_if(iterable, unary_predicate):
    """
    Returns the number of items in iterable for which unary_predicate
    returns True.
    """
    return sum(1 for item in iterable if unary_predicate(item))


def find_if(iterable, unary_predicate):
    """
    Returns the first element for which unary_predicate returns True.
    Returns None if no such element could be found.
    """
    return next((item for item in iterable if unary_predicate(item)), None)


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


# PRETTY_TIMESTAMP_FORMAT_STR = '%B %d, %Y %I:%M:%S %p'

FILESYSTEM_TIMESTAMP_FORMAT_STR = '%Y-%m-%d %H.%M.%S'


# -----------------------------------------------------------------------------
# -----------------------------------------------------------------------------
# -----------------------------------------------------------------------------

def check_values_against_whitelist(values, whitelist):
    """
    values -- An iterable object.
    whitelist -- A regular expression (can be compiled or a string).

    Raises ValidationError if any value in values does not fully match the
    whitelist regex (as per regex.fullmatch
    https://docs.python.org/3.4/library/re.html#re.regex.fullmatch)
    """
    for value in values:
        if not re.fullmatch(whitelist, value):
            raise ValidationError(
                "Value {0} contains illegal characters.".format(
                    value, whitelist))


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
        raise ValidationError("Filenames must be non-null")

    if not filename and not allow_empty:
        raise ValidationError("Filenames must be non-empty")

    if not gc.PROJECT_FILENAME_WHITELIST_REGEX.fullmatch(filename):
        raise ValidationError(
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
        raise ValidationError("File patterns must be non-empty")

    if not gc.PROJECT_FILE_PATTERN_WHITELIST_REGEX.fullmatch(pattern):
        raise ValidationError(
            "Invalid file pattern: {0} \n"
            "Shell-style patterns must only contain "
            "alphanumeric characters, hyphen, underscore, "
            "period, * ? [ ] and !".format(pattern))


# -----------------------------------------------------------------------------
# -----------------------------------------------------------------------------
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
        get_project_relative_root_dir(project), gc.PROJECT_FILES_DIRNAME)


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
        get_project_relative_root_dir(project), gc.PROJECT_SUBMISSIONS_DIRNAME)


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


# -----------------------------------------------------------------------------
# -----------------------------------------------------------------------------
# -----------------------------------------------------------------------------

class ChangeDirectory(object):
    """
    Enables moving into and out of a given directory using "with" statements.
    """

    def __init__(self, new_dir):
        self._original_dir = os.getcwd()
        self._new_dir = new_dir

    def __enter__(self):
        os.chdir(self._new_dir)

    def __exit__(self, *args):
        os.chdir(self._original_dir)


class TemporaryFile(object):
    """
    Enables creating and destroying a temporary file using "with" statements.
    """

    def __init__(self, filename, file_contents):
        self.filename = filename
        self.file_contents = file_contents

    def __enter__(self):
        with open(self.filename, 'w') as f:
            f.write(self.file_contents)

    def __exit__(self, *args):
        os.remove(self.filename)


class TemporaryDirectory(object):
    """
    Enables creating and destroying a temporary directory using
    "with" statements.
    Note that when the directory is destroyed, any files inside it
    will be destroyed as well.
    """

    def __init__(self, dirname):
        self.dirname = dirname

    def __enter__(self):
        os.mkdir(self.dirname)
        os.chmod(self.dirname, 0o777)

    def __exit__(self, *args):
        shutil.rmtree(self.dirname)
