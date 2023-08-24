from __future__ import annotations

import datetime
import enum
import os
import re
import subprocess
import typing
from typing import List, Tuple, Type, TypeVar, cast

from backports import zoneinfo

from django.conf import settings
from django.core import exceptions
from django.utils import timezone

from . import constants as const

if typing.TYPE_CHECKING:
    from .models.course import Course
    from .models.group import Group
    from .models.project import Project
    from .models.submission import Submission


class DiffResult:
    def __init__(self, diff_pass: bool, diff_content: List[str]):
        self.diff_pass = diff_pass
        self.diff_content = diff_content


_DIFF_LINE_REGEX = re.compile(r'^(?:  |\+ |- ).*\n+'.encode(), flags=re.MULTILINE)


def get_diff(first_filename: str, second_filename: str,
             ignore_case: bool = False,
             ignore_whitespace: bool = False,
             ignore_whitespace_changes: bool = False,
             ignore_blank_lines: bool = False) -> DiffResult:
    """
    Diffs first and second using the GNU diff command line utility.
    Returns an empty list if first and second are considered equivalent.
    Otherwise, returns a list of strings, each of which are prefixed
    with one of the two-letter opcodes used by
    https://docs.python.org/3.5/library/difflib.html#difflib.Differ
    """
    # We're adding newlines at the beginning of each formatted line
    # because GNU diff will otherwise handle missing trailing
    # newlines in a way that the client can't reliably parse.
    diff_cmd = ['diff',
                '--text',  # Consider all files to be text
                '--new-line-format', '+ %L\n',
                '--old-line-format', '- %L\n',
                '--unchanged-line-format', '  %L\n']
    if ignore_case:
        diff_cmd.append('--ignore-case')
    if ignore_whitespace:
        diff_cmd.append('--ignore-all-space')
    if ignore_whitespace_changes:
        diff_cmd.append('--ignore-space-change')
    if ignore_blank_lines:
        diff_cmd.append('--ignore-blank-lines')

    diff_cmd += [first_filename, second_filename]

    diff_result = subprocess.run(diff_cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
    diff_list = [match.group()[:-1].decode('utf-8', 'surrogateescape')
                 for match in _DIFF_LINE_REGEX.finditer(diff_result.stdout)]
    return DiffResult(diff_result.returncode == 0, diff_list)


def get_24_hour_period(
    start_time: datetime.time,
    contains_datetime: datetime.datetime,
    convert_result_to_utc: bool = True
) -> Tuple[datetime.datetime, datetime.datetime]:
    """
    Returns a tuple (start_datetime, end_datetime) representing a 24
    hour period that contains the current date and time and with the
    start and end time both being start_time.
    """
    start_date = contains_datetime.date()
    if contains_datetime.time() < start_time:
        start_date += timezone.timedelta(days=-1)

    start_datetime = timezone.datetime.combine(
        start_date, start_time)
    start_datetime = start_datetime.replace(
        tzinfo=zoneinfo.ZoneInfo(str(contains_datetime.tzinfo))  # type: ignore
    )
    end_datetime = start_datetime + timezone.timedelta(days=1)

    if convert_result_to_utc:
        return (
            start_datetime.astimezone(zoneinfo.ZoneInfo('UTC')),  # type: ignore
            end_datetime.astimezone(zoneinfo.ZoneInfo('UTC'))  # type: ignore
        )

    return start_datetime, end_datetime


def check_filename(filename: str) -> None:
    """
    Verifies whether the given filename is valid according to the
    following requirements:
        - Filenames must be non-empty and non-null
        - Filenames must not include directories.
        - Filenames must not be '..' or '.'.

    If the given filename does not meet these requirements, ValidationError
    is raised.
    """
    if not filename:
        raise exceptions.ValidationError("Filenames must not be empty.")

    if os.path.basename(filename) != filename:
        raise exceptions.ValidationError('Filenames must not include directories.')

    if filename == '..' or filename == '.':
        raise exceptions.ValidationError('Filenames must not be ".." or ".".')

# -----------------------------------------------------------------------------


def get_course_root_dir(course: Course) -> str:
    """
    Computes the absolute path of the base directory for the given course.
    """
    return os.path.join(
        settings.MEDIA_ROOT, get_course_relative_root_dir(course))


def get_course_relative_root_dir(course: Course) -> str:
    """
    Same as get_course_root_dir() but returns a path that is
    relative to MEDIA_ROOT.
    """
    return os.path.join('courses', 'course{}'.format(course.pk))


def get_project_root_dir(project: Project) -> str:
    """
    Computes the absolute path of the base directory for the given project.
    """
    return os.path.join(settings.MEDIA_ROOT, get_project_relative_root_dir(project))


def get_project_relative_root_dir(project: Project) -> str:
    """
    Same as get_project_root_dir() but returns a path that is
    relative to MEDIA_ROOT.
    """
    return os.path.join(
        get_course_relative_root_dir(project.course),
        'project{}'.format(project.pk))


def get_project_files_dir(project: Project) -> str:
    """
    Computes the absolute path of the directory where uploaded files
    should be stored for the given project.
    """
    return os.path.join(settings.MEDIA_ROOT, get_project_files_relative_dir(project))


def get_project_files_relative_dir(project: Project) -> str:
    """
    Same as get_project_files_dir() but returns a path that is
    relative to MEDIA_ROOT.
    """
    return os.path.join(get_project_relative_root_dir(project), const.PROJECT_FILES_DIRNAME)


def get_project_groups_dir(project: Project) -> str:
    """
    Computes the absolute path of the directory where student submission
    groups should be stored for the given project.
    """
    return os.path.join(
        settings.MEDIA_ROOT,
        get_project_groups_relative_dir(project))


def get_project_groups_relative_dir(project: Project) -> str:
    """
    Same as get_project_groups_dir() but returns a path
    that is relative to MEDIA_ROOT.
    """
    return os.path.join(
        get_project_relative_root_dir(project),
        const.PROJECT_SUBMISSIONS_DIRNAME)


def get_student_group_dir(group: Group) -> str:
    """
    Computes the absolute path of the directory where submissions for the
    given group should be stored.
    """
    return os.path.join(settings.MEDIA_ROOT, get_student_group_relative_dir(group))


def get_student_group_relative_dir(group: Group) -> str:
    """
    Same as get_student_group_dir() but returns a path that is
    relative to MEDIA_ROOT.
    """
    return os.path.join(get_project_groups_relative_dir(group.project), 'group{}'.format(group.pk))


def get_submission_dir(submission: Submission) -> str:
    """
    Computes the absolute path of the directory where files included
    in the given submission should be stored.
    """
    return os.path.join(
        settings.MEDIA_ROOT,
        get_submission_relative_dir(submission))


def get_submission_relative_dir(submission: Submission) -> str:
    """
    Same as get_submission_dir() but returns a path that is relative to
    MEDIA_ROOT.
    """
    return os.path.join(
        get_student_group_relative_dir(submission.group),
        get_submission_dir_basename(submission))


def get_submission_dir_basename(submission: Submission) -> str:
    return 'submission{}'.format(submission.pk)


def get_result_output_dir(submission: Submission) -> str:
    return os.path.join(get_submission_dir(submission), 'output')


def misc_cmd_output_dir() -> str:
    return os.path.join(settings.MEDIA_ROOT, 'misc_cmd_output')


# -----------------------------------------------------------------------------

_OrderedEnumDerived = TypeVar('_OrderedEnumDerived', bound=enum.Enum)


class OrderedEnum(enum.Enum):
    """
    In addition to the core properties of enum.Enum, OrderedEnums are comparable using
    <, >, <=, and >=. The ordering of enum values is the same as the order they are defined in.

    Example:
    >>> class MyEnum(OrderedEnum):
    ...:    spam = 'spam'
    ...:    egg = 'egg'
    ...:
    >>> print(MyEnum.spam < MyEnum.egg)
    True
    >>> print(MyEnum.spam > MyEnum.egg)
    False
    """
    _weight: int

    # Adopted from https://docs.python.org/3.5/library/enum.html#autonumber
    def __new__(cls: Type[_OrderedEnumDerived], value: object) -> _OrderedEnumDerived:
        obj = object.__new__(cls)
        obj._value_ = value
        # OrderedEnum values are ordered by _weight.
        obj._weight = len(cls.__members__)  # type: ignore
        return obj

    # Comparators adopted from https://docs.python.org/3.5/library/enum.html#orderedenum
    def __ge__(self, other: OrderedEnum) -> bool:
        if self.__class__ is other.__class__:
            return self._weight >= other._weight

        return NotImplemented

    def __gt__(self, other: OrderedEnum) -> bool:
        if self.__class__ is other.__class__:
            return self._weight > other._weight

        return NotImplemented

    def __le__(self, other: OrderedEnum) -> bool:
        if self.__class__ is other.__class__:
            return self._weight <= other._weight

        return NotImplemented

    def __lt__(self, other: OrderedEnum) -> bool:
        if self.__class__ is other.__class__:
            return self._weight < other._weight

        return NotImplemented

    @classmethod
    def get_min(cls: Type[_OrderedEnumDerived]) -> _OrderedEnumDerived:
        return list(cls)[0]

    @classmethod
    def get_max(cls: Type[_OrderedEnumDerived]) -> _OrderedEnumDerived:
        return list(cls)[-1]
