import os

from django.test import TestCase
from django.conf import settings
from django.core.exceptions import ValidationError

import autograder.core.models as ag_models

import autograder.utils.testing as test_ut
import autograder.core.constants as const
import autograder.core.utils as core_ut

import autograder.utils.testing.model_obj_builders as obj_build


class CheckUserProvidedFilenameTest(TestCase):
    def test_valid_filename(self):
        core_ut.check_user_provided_filename('spAM-eggs_42.cpp')

    def test_exception_on_file_path_given(self):
        with self.assertRaises(ValidationError):
            core_ut.check_user_provided_filename('../spam.txt')

        with self.assertRaises(ValidationError):
            core_ut.check_user_provided_filename('..')

    def test_exception_on_filename_with_shell_chars(self):
        with self.assertRaises(ValidationError):
            core_ut.check_user_provided_filename('; echo "haxorz"; # ')

    def test_exception_on_filename_starts_with_dot(self):
        with self.assertRaises(ValidationError):
            core_ut.check_user_provided_filename('.spameggs')

    def test_exception_null_filename(self):
        with self.assertRaises(ValidationError):
            core_ut.check_user_provided_filename(None)
            core_ut.check_user_provided_filename(None, allow_empty=True)

    def test_exception_empty_filename(self):
        with self.assertRaises(ValidationError):
            core_ut.check_user_provided_filename('')

    def test_no_exception_empty_filename_allowed(self):
        core_ut.check_user_provided_filename('', allow_empty=True)


class FileSystemUtilTestCase(test_ut.UnitTestBase):
    def setUp(self):
        self.group = obj_build.build_submission_group()
        self.project = self.group.project
        self.course = self.project.course

        self.group_dir_basename = 'group{}'.format(self.group.pk)
        self.course_dirname = 'course{}'.format(self.course.pk)
        self.project_dirname = 'project{}'.format(self.project.pk)

    def test_get_course_root_dir(self):
        expected_relative = "{0}/{1}".format(
            const.FILESYSTEM_ROOT_COURSES_DIRNAME,
            self.course_dirname)

        actual_relative = core_ut.get_course_relative_root_dir(self.course)
        self.assertEqual(expected_relative, actual_relative)

        expected_absolute = os.path.join(
            settings.MEDIA_ROOT, expected_relative)

        actual_absolute = core_ut.get_course_root_dir(self.course)
        self.assertEqual(expected_absolute, actual_absolute)

    def test_get_project_root_dir(self):
        expected_relative = "{0}/{1}/{2}".format(
            const.FILESYSTEM_ROOT_COURSES_DIRNAME,
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
            const.FILESYSTEM_ROOT_COURSES_DIRNAME,
            self.course_dirname,
            self.project_dirname, const.PROJECT_FILES_DIRNAME)

        actual_relative = core_ut.get_project_files_relative_dir(self.project)
        self.assertEqual(expected_relative, actual_relative)

        expected_absolute = os.path.join(
            settings.MEDIA_ROOT, expected_relative)

        actual_absolute = core_ut.get_project_files_dir(self.project)
        self.assertEqual(expected_absolute, actual_absolute)

    def test_get_project_submission_groups_dir(self):
        expected_relative = "{0}/{1}/{2}/{3}".format(
            const.FILESYSTEM_ROOT_COURSES_DIRNAME,
            self.course_dirname,
            self.project_dirname,
            const.PROJECT_SUBMISSIONS_DIRNAME)
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
            const.FILESYSTEM_ROOT_COURSES_DIRNAME,
            self.course_dirname,
            self.project_dirname,
            const.PROJECT_SUBMISSIONS_DIRNAME,
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
            const.FILESYSTEM_ROOT_COURSES_DIRNAME,
            self.course_dirname,
            self.project_dirname,
            const.PROJECT_SUBMISSIONS_DIRNAME,
            self.group_dir_basename,
            submission_dir_basename)

        actual_relative = core_ut.get_submission_relative_dir(submission)
        self.assertEqual(expected_relative, actual_relative)

        expected_absolute = os.path.join(
            settings.MEDIA_ROOT, expected_relative)
        actual_absolute = core_ut.get_submission_dir(submission)
        self.assertEqual(expected_absolute, actual_absolute)
