import datetime
import os
import tempfile

import pytz
from django.conf import settings
from django.core.exceptions import ValidationError
from django.test import SimpleTestCase

import autograder.core.models as ag_models
import autograder.core.utils as core_ut
import autograder.utils.testing.model_obj_builders as obj_build
from autograder.core import constants
from autograder.utils.testing import UnitTestBase


class DiffTestCase(SimpleTestCase):
    def setUp(self):
        super().setUp()
        self.file1 = tempfile.NamedTemporaryFile()
        self.file2 = tempfile.NamedTemporaryFile()

    def tearDown(self):
        super().tearDown()
        self.file1.close()
        self.file2.close()

    def _write_and_seek(self, file_, content):
        if isinstance(content, str):
            content = content.encode()
        file_.write(content)
        file_.seek(0)

    def test_diff_content(self):
        self._write_and_seek(self.file1, '\n'.join(('q', 'a', 'b', 'x', 'c', 'd', 'e\n')))
        self._write_and_seek(self.file2, '\n'.join(('a', 'b', 'y', 'c', 'd', 'f', 'e\n')))

        expected = [
            '- q\n',
            '  a\n',
            '  b\n',
            '- x\n',
            '+ y\n',
            '  c\n',
            '  d\n',
            '+ f\n',
            '  e\n'
        ]

        diff = core_ut.get_diff(self.file1.name, self.file2.name)

        self.assertEqual(expected, list(diff.diff_content))

    def test_trailing_newline_missing(self):
        self._write_and_seek(self.file1, '''egg
sausage''')
        self._write_and_seek(self.file2, '''spam
egg
sausage
''')

        expected = [
            '+ spam\n',
            '  egg\n',
            '- sausage',
            '+ sausage\n'
        ]
        diff = core_ut.get_diff(self.file1.name, self.file2.name)
        self.assertEqual(expected, list(diff.diff_content))

    def test_diff_delta_strs_in_files(self):
        self._write_and_seek(self.file1, '''egg+ cheese
spam- sausage
''')
        self._write_and_seek(self.file2, '''egg
cheese
sausage''')
        expected = [
            '- egg+ cheese\n',
            '- spam- sausage\n',
            '+ egg\n',
            '+ cheese\n',
            '+ sausage'
        ]
        diff = core_ut.get_diff(self.file1.name, self.file2.name)
        self.assertEqual(expected, list(diff.diff_content))

    def test_weird_line_endings(self):
        self._write_and_seek(self.file1, '''egg
\r
cheese''')
        self._write_and_seek(self.file2, '''egg
cheese\r
''')
        expected = [
            '  egg\n',
            '- \r\n',
            '- cheese',
            '+ cheese\r\n'
        ]
        diff = core_ut.get_diff(self.file1.name, self.file2.name)
        self.assertEqual(expected, list(diff.diff_content))

    def test_non_utf_chars(self):
        non_utf_bytes = b'\x80 and some other stuff just because\n'

        self._write_and_seek(self.file1, b'some stuff')
        self._write_and_seek(self.file2, non_utf_bytes)

        expected_diff = [
            '- some stuff',
            '+ ' + non_utf_bytes.decode('utf-8', 'surrogateescape')]
        diff = core_ut.get_diff(self.file1.name, self.file2.name)
        self.assertEqual(expected_diff, diff.diff_content)

    # If diff sees a null byte, it will just print
    # "Binary Files X and Y differ" by default. We want to make sure
    # that we are passing the --text flag to diff.
    def test_text_flag_passed_to_gnu_diff(self) -> None:
        non_utf_bytes = b'\x00 I am null byte\n'

        self._write_and_seek(self.file1, b'some stuff')
        self._write_and_seek(self.file2, non_utf_bytes)

        expected_diff = [
            '- some stuff',
            '+ ' + non_utf_bytes.decode('utf-8', 'surrogateescape')]
        diff = core_ut.get_diff(self.file1.name, self.file2.name)
        self.assertEqual(expected_diff, diff.diff_content)

    def test_ignore_case(self):
        self._write_and_seek(self.file1, 'SPAM')
        self._write_and_seek(self.file2, 'spam')
        result = core_ut.get_diff(self.file1.name, self.file2.name, ignore_case=True)
        self.assertTrue(result.diff_pass)

    def test_ignore_whitespace(self):
        self._write_and_seek(self.file1, 'spam egg')
        self._write_and_seek(self.file2, '   spam   \tegg  ')
        result = core_ut.get_diff(self.file1.name, self.file2.name, ignore_whitespace=True)
        self.assertTrue(result.diff_pass)

    def test_ignore_whitespace_changes(self):
        self._write_and_seek(self.file1, 'spam egg')
        self._write_and_seek(self.file2, 'spam   \tegg')
        result = core_ut.get_diff(self.file1.name, self.file2.name, ignore_whitespace_changes=True)
        self.assertTrue(result.diff_pass)

    def test_ignore_blank_lines(self):
        self._write_and_seek(self.file1, 'spam\n\n\negg\n')
        self._write_and_seek(self.file2, 'spam\negg\n')
        result = core_ut.get_diff(self.file1.name, self.file2.name, ignore_blank_lines=True)
        self.assertTrue(result.diff_pass)

    def test_all_ignore_options(self):
        self._write_and_seek(self.file1, 'spam sausage\n\n\negg\n')
        self._write_and_seek(self.file2, 'SPAM   \tsausage\negg\n')
        result = core_ut.get_diff(self.file1.name, self.file2.name,
                                  ignore_case=True,
                                  ignore_whitespace=True,
                                  ignore_whitespace_changes=True,
                                  ignore_blank_lines=True)
        self.assertTrue(result.diff_pass)


class Get24HourPeriodTestCase(SimpleTestCase):
    def test_dst_start(self):
        # Make sure that our date computations work correctly
        # on the first day of daylight savings time.
        reset_time = datetime.time(0, 0, 0)
        reset_timezone = pytz.timezone('US/Eastern')
        # Set up the current time the same way as in
        # Group.num_submits_towards_limit
        current_time = datetime.datetime(
            2022, 3, 13, 11, tzinfo=pytz.timezone('UTC')
        ).astimezone(reset_timezone)

        start, end = core_ut.get_24_hour_period(reset_time, current_time)
        self.assertEqual(
            datetime.datetime(2022, 3, 13, 5, tzinfo=pytz.timezone('UTC')),
            start
        )
        self.assertEqual(
            datetime.datetime(2022, 3, 14, 4, tzinfo=pytz.timezone('UTC')),
            end
        )


class CheckFilenameTest(SimpleTestCase):
    def test_valid_filename(self):
        core_ut.check_filename('spAM-eggs_42.cpp')

    def test_bad_filenames(self):
        for filename in ('', '..', '.', '/spam', '../spam'):
            with self.assertRaises(ValidationError):
                core_ut.check_filename(filename)


class FileSystemUtilTestCase(UnitTestBase):
    def setUp(self):
        super().setUp()

        self.group = obj_build.build_group()
        self.project = self.group.project
        self.course = self.project.course

        self.group_dir_basename = 'group{}'.format(self.group.pk)
        self.course_dirname = 'course{}'.format(self.course.pk)
        self.project_dirname = 'project{}'.format(self.project.pk)

    def test_get_course_root_dir(self):
        expected_relative = "{0}/{1}".format(
            constants.FILESYSTEM_ROOT_COURSES_DIRNAME,
            self.course_dirname)

        actual_relative = core_ut.get_course_relative_root_dir(self.course)
        self.assertEqual(expected_relative, actual_relative)

        expected_absolute = os.path.join(
            settings.MEDIA_ROOT, expected_relative)

        actual_absolute = core_ut.get_course_root_dir(self.course)
        self.assertEqual(expected_absolute, actual_absolute)

    def test_get_project_root_dir(self):
        expected_relative = "{0}/{1}/{2}".format(
            constants.FILESYSTEM_ROOT_COURSES_DIRNAME,
            self.course_dirname,
            self.project_dirname)

        actual_relative = core_ut.get_project_relative_root_dir(self.project)
        self.assertEqual(expected_relative, actual_relative)

        expected_absolute = os.path.join(
            settings.MEDIA_ROOT, expected_relative)

        actual_absolute = core_ut.get_project_root_dir(self.project)
        self.assertEqual(expected_absolute, actual_absolute)

    def test_get_project_files_dir(self):
        expected_relative = "{0}/{1}/{2}/{3}".format(
            constants.FILESYSTEM_ROOT_COURSES_DIRNAME,
            self.course_dirname,
            self.project_dirname, constants.PROJECT_FILES_DIRNAME)

        actual_relative = core_ut.get_project_files_relative_dir(self.project)
        self.assertEqual(expected_relative, actual_relative)

        expected_absolute = os.path.join(
            settings.MEDIA_ROOT, expected_relative)

        actual_absolute = core_ut.get_project_files_dir(self.project)
        self.assertEqual(expected_absolute, actual_absolute)

    def test_get_project_groups_dir(self):
        expected_relative = "{0}/{1}/{2}/{3}".format(
            constants.FILESYSTEM_ROOT_COURSES_DIRNAME,
            self.course_dirname,
            self.project_dirname,
            constants.PROJECT_SUBMISSIONS_DIRNAME)
        actual_relative = core_ut.get_project_groups_relative_dir(
            self.project)
        self.assertEqual(expected_relative, actual_relative)

        expected_absolute = os.path.join(
            settings.MEDIA_ROOT, expected_relative)
        actual_absolute = core_ut.get_project_groups_dir(
            self.project)
        self.assertEqual(expected_absolute, actual_absolute)

    def test_get_student_group_dir(self):
        expected_relative = "{0}/{1}/{2}/{3}/{4}".format(
            constants.FILESYSTEM_ROOT_COURSES_DIRNAME,
            self.course_dirname,
            self.project_dirname,
            constants.PROJECT_SUBMISSIONS_DIRNAME,
            self.group_dir_basename)

        actual_relative = core_ut.get_student_group_relative_dir(
            self.group)
        self.assertEqual(expected_relative, actual_relative)

        expected_absolute = os.path.join(
            settings.MEDIA_ROOT, expected_relative)
        actual_absolute = core_ut.get_student_group_dir(self.group)

        self.assertEqual(expected_absolute, actual_absolute)

    def test_get_submission_dir(self):
        submission = ag_models.Submission.objects.validate_and_create(
            group=self.group, submitted_files=[])
        submission_dir_basename = 'submission{}'.format(submission.pk)

        expected_relative = "{0}/{1}/{2}/{3}/{4}/{5}".format(
            constants.FILESYSTEM_ROOT_COURSES_DIRNAME,
            self.course_dirname,
            self.project_dirname,
            constants.PROJECT_SUBMISSIONS_DIRNAME,
            self.group_dir_basename,
            submission_dir_basename)

        actual_relative = core_ut.get_submission_relative_dir(submission)
        self.assertEqual(expected_relative, actual_relative)

        expected_absolute = os.path.join(
            settings.MEDIA_ROOT, expected_relative)
        actual_absolute = core_ut.get_submission_dir(submission)
        self.assertEqual(expected_absolute, actual_absolute)

    def test_get_result_output_dir(self):
        submission = ag_models.Submission.objects.validate_and_create(
            group=self.group, submitted_files=[])

        submission_dir_basename = 'submission{}'.format(submission.pk)

        expected_absolute = os.path.join(
            settings.MEDIA_ROOT,
            "{0}/{1}/{2}/{3}/{4}/{5}/{6}".format(
                constants.FILESYSTEM_ROOT_COURSES_DIRNAME,
                self.course_dirname,
                self.project_dirname,
                constants.PROJECT_SUBMISSIONS_DIRNAME,
                self.group_dir_basename,
                submission_dir_basename,
                constants.FILESYSTEM_RESULT_OUTPUT_DIRNAME))

        actual_absolute = core_ut.get_result_output_dir(submission)
        self.assertEqual(expected_absolute, actual_absolute)

# -----------------------------------------------------------------------------


class MyOrderedEnum(core_ut.OrderedEnum):
    spam = 'spam'
    egg = 'egg'


class OrderedEnumTestCase(SimpleTestCase):
    def test_comparison(self):
        self.assertTrue(MyOrderedEnum.spam < MyOrderedEnum.egg)
        self.assertFalse(MyOrderedEnum.spam > MyOrderedEnum.egg)

        self.assertTrue(MyOrderedEnum.spam <= MyOrderedEnum.egg)
        self.assertFalse(MyOrderedEnum.spam >= MyOrderedEnum.egg)

        self.assertTrue(MyOrderedEnum.egg > MyOrderedEnum.spam)
        self.assertFalse(MyOrderedEnum.egg < MyOrderedEnum.spam)

        self.assertTrue(MyOrderedEnum.egg >= MyOrderedEnum.spam)
        self.assertFalse(MyOrderedEnum.egg <= MyOrderedEnum.spam)

        self.assertTrue(MyOrderedEnum.spam <= MyOrderedEnum.spam)
        self.assertTrue(MyOrderedEnum.egg >= MyOrderedEnum.egg)

    def test_get_min(self):
        self.assertEqual(MyOrderedEnum.spam, MyOrderedEnum.get_min())

    def test_get_max(self):
        self.assertEqual(MyOrderedEnum.egg, MyOrderedEnum.get_max())
