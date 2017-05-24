import os

from django.test import TestCase
from django.conf import settings
from django.core.exceptions import ValidationError

import autograder.core.models as ag_models

from autograder.utils.testing import UnitTestBase
from autograder.core import constants
import autograder.core.utils as core_ut

import autograder.utils.testing.model_obj_builders as obj_build


class DiffTestCase(TestCase):
    def test_diff_content(self):
        str1 = '\n'.join(('q', 'a', 'b', 'x', 'c', 'd', 'e\n'))
        str2 = '\n'.join(('a', 'b', 'y', 'c', 'd', 'f', 'e\n'))

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

        diff = core_ut.get_diff(str1, str2)

        self.assertEqual(expected, list(diff))

    def test_ignore_case(self):
        str1 = 'SPAM'
        str2 = 'spam'
        self.assertEqual([], core_ut.get_diff(str1, str2, ignore_case=True))

    def test_ignore_whitespace(self):
        str1 = 'spam egg'
        str2 = '   spam   \tegg  '
        self.assertEqual(
            [], core_ut.get_diff(str1, str2, ignore_whitespace=True))

    def test_ignore_whitespace_changes(self):
        str1 = 'spam egg'
        str2 = 'spam   \tegg'
        self.assertEqual(
            [], core_ut.get_diff(str1, str2, ignore_whitespace_changes=True))

    def test_ignore_blank_lines(self):
        str1 = 'spam\n\n\negg\n'
        str2 = 'spam\negg\n'
        self.assertEqual(
            [], core_ut.get_diff(str1, str2, ignore_blank_lines=True))

    def test_all_ignore_options(self):
        str1 = 'spam sausage\n\n\negg\n'
        str2 = 'SPAM   \tsausage\negg\n'
        self.assertEqual([],
                         core_ut.get_diff(
                             str1, str2,
                             ignore_case=True,
                             ignore_whitespace=True,
                             ignore_whitespace_changes=True,
                             ignore_blank_lines=True))


class CheckFilenameTest(TestCase):
    def test_valid_filename(self):
        core_ut.check_filename('spAM-eggs_42.cpp')

    def test_bad_filenames(self):
        for filename in ('', '..', '.', '/spam', '../spam'):
            with self.assertRaises(ValidationError):
                core_ut.check_filename(filename)


class FileSystemUtilTestCase(UnitTestBase):
    def setUp(self):
        self.group = obj_build.build_submission_group()
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

    def test_get_project_submission_groups_dir(self):
        expected_relative = "{0}/{1}/{2}/{3}".format(
            constants.FILESYSTEM_ROOT_COURSES_DIRNAME,
            self.course_dirname,
            self.project_dirname,
            constants.PROJECT_SUBMISSIONS_DIRNAME)
        actual_relative = core_ut.get_project_submission_groups_relative_dir(
            self.project)
        self.assertEqual(expected_relative, actual_relative)

        expected_absolute = os.path.join(
            settings.MEDIA_ROOT, expected_relative)
        actual_absolute = core_ut.get_project_submission_groups_dir(
            self.project)
        self.assertEqual(expected_absolute, actual_absolute)

    def test_get_student_submission_group_dir(self):
        expected_relative = "{0}/{1}/{2}/{3}/{4}".format(
            constants.FILESYSTEM_ROOT_COURSES_DIRNAME,
            self.course_dirname,
            self.project_dirname,
            constants.PROJECT_SUBMISSIONS_DIRNAME,
            self.group_dir_basename)

        actual_relative = core_ut.get_student_submission_group_relative_dir(
            self.group)
        self.assertEqual(expected_relative, actual_relative)

        expected_absolute = os.path.join(
            settings.MEDIA_ROOT, expected_relative)
        actual_absolute = core_ut.get_student_submission_group_dir(self.group)

        self.assertEqual(expected_absolute, actual_absolute)

    def test_get_submission_dir(self):
        submission = ag_models.Submission.objects.validate_and_create(
            submission_group=self.group, submitted_files=[])
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

# -----------------------------------------------------------------------------


class MyOrderedEnum(core_ut.OrderedEnum):
    spam = 'spam'
    egg = 'egg'


class OrderedEnumTestCase(TestCase):
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
