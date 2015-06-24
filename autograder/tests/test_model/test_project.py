import os
import datetime

from django.core.exceptions import ValidationError
from django.db.utils import IntegrityError
from django.utils import timezone

from autograder.models import Project, Semester, Course

import autograder.shared.utilities as ut

from autograder.tests.temporary_filesystem_test_case import (
    TemporaryFilesystemTestCase)


_FILENAME_WITH_SHELL_CHARS = '; echo "haxorz"; # '


class ProjectTestCase(TemporaryFilesystemTestCase):
    def setUp(self):
        super().setUp()
        self.course = Course.objects.create(name='eecs280')
        self.semester = Semester.objects.create(name='f15', course=self.course)
        self.PROJECT_NAME = 'stats_project'

    # -------------------------------------------------------------------------
    # -------------------------------------------------------------------------

    def test_valid_create_with_defaults(self):
        new_project = Project.objects.create(
            name=self.PROJECT_NAME, semester=self.semester)

        loaded_project = Project.get_by_composite_key(
            self.PROJECT_NAME, self.semester)

        self.assertEqual(loaded_project, new_project)
        self.assertEqual(loaded_project.name, new_project.name)
        self.assertEqual(loaded_project.semester, new_project.semester)

        self.assertEqual(loaded_project.project_files, [])
        self.assertEqual(loaded_project.visible_to_students, False)
        self.assertEqual(loaded_project.closing_time, None)
        self.assertEqual(loaded_project.disallow_student_submissions, False)
        self.assertEqual(loaded_project.min_group_size, 1)
        self.assertEqual(loaded_project.max_group_size, 1)
        self.assertEqual(loaded_project.required_student_files, [])
        self.assertEqual(loaded_project.expected_student_file_patterns, {})

    # -------------------------------------------------------------------------

    def test_valid_create_non_defaults(self):
        tomorrow_date = timezone.now() + datetime.timedelta(days=1)
        min_group_size = 2
        max_group_size = 5
        required_student_files = ["spam.cpp", "eggs.cpp"]
        expected_student_file_patterns = {
            "test_*.cpp": [1, 10], "test[0-9].cpp": [2, 2],
            "test[!0-9]?.cpp": [3, 5]
        }

        new_project = Project.objects.create(
            name=self.PROJECT_NAME,
            semester=self.semester,
            visible_to_students=True,
            closing_time=tomorrow_date,
            disallow_student_submissions=True,
            min_group_size=min_group_size,
            max_group_size=max_group_size,
            required_student_files=required_student_files,
            expected_student_file_patterns=expected_student_file_patterns
        )

        loaded_project = Project.get_by_composite_key(
            self.PROJECT_NAME, self.semester)

        self.assertEqual(loaded_project, new_project)
        self.assertEqual(loaded_project.name, new_project.name)
        self.assertEqual(loaded_project.semester, new_project.semester)

        self.assertEqual(loaded_project.visible_to_students, True)
        self.assertEqual(loaded_project.closing_time, tomorrow_date)
        self.assertEqual(loaded_project.disallow_student_submissions, True)
        self.assertEqual(loaded_project.min_group_size, min_group_size)
        self.assertEqual(loaded_project.max_group_size, max_group_size)
        self.assertEqual(
            loaded_project.required_student_files, required_student_files)
        self.assertEqual(
            loaded_project.expected_student_file_patterns,
            expected_student_file_patterns)

    # -------------------------------------------------------------------------

    def test_exception_on_empty_name(self):
        with self.assertRaises(ValidationError):
            Project.objects.create(name='', semester=self.semester)

    # -------------------------------------------------------------------------

    def test_exception_on_null_name(self):
        with self.assertRaises(ValidationError):
            Project.objects.create(name=None, semester=self.semester)

    # -------------------------------------------------------------------------

    def test_exception_on_non_unique_name(self):
        Project.objects.create(name=self.PROJECT_NAME, semester=self.semester)
        with self.assertRaises(IntegrityError):
            Project.objects.create(
                name=self.PROJECT_NAME, semester=self.semester)

    # -------------------------------------------------------------------------

    def test_no_exception_same_name_different_semester(self):
        new_semester_name = 'w16'
        new_semester = Semester.objects.create(
            name=new_semester_name, course=self.course)

        Project.objects.create(name=self.PROJECT_NAME, semester=self.semester)
        new_project = Project.objects.create(
            name=self.PROJECT_NAME, semester=new_semester)

        loaded_new_project = Project.get_by_composite_key(
            self.PROJECT_NAME, new_semester)

        self.assertEqual(loaded_new_project, new_project)
        self.assertEqual(loaded_new_project.name, new_project.name)
        self.assertEqual(loaded_new_project.semester, new_project.semester)

    # -------------------------------------------------------------------------

    def test_no_exception_same_semester_and_project_names_different_course(self):
        new_course_name = 'eecs381'
        new_course = Course.objects.create(name=new_course_name)
        new_semester = Semester.objects.create(
            name=self.semester.name, course=new_course)

        Project.objects.create(name=self.PROJECT_NAME, semester=self.semester)
        new_project = Project.objects.create(
            name=self.PROJECT_NAME, semester=new_semester)

        loaded_new_project = Project.get_by_composite_key(
            self.PROJECT_NAME, new_semester)

        self.assertEqual(loaded_new_project, new_project)
        self.assertEqual(loaded_new_project.name, new_project.name)
        self.assertEqual(loaded_new_project.semester, new_project.semester)

        self.assertNotEqual(
            loaded_new_project.semester.course, self.course)

    # -------------------------------------------------------------------------

    def test_exception_on_min_group_size_too_small(self):
        with self.assertRaises(ValidationError):
            Project.objects.create(
                name=self.PROJECT_NAME, semester=self.semester,
                min_group_size=0)

    # -------------------------------------------------------------------------

    def test_exception_on_max_group_size_too_small(self):
        with self.assertRaises(ValidationError):
            Project.objects.create(
                name=self.PROJECT_NAME, semester=self.semester,
                max_group_size=0)

    # -------------------------------------------------------------------------

    def test_exception_on_max_group_size_smaller_than_min_group_size(self):
        with self.assertRaises(ValidationError):
            Project.objects.create(
                name=self.PROJECT_NAME, semester=self.semester,
                min_group_size=3, max_group_size=2)

    # -------------------------------------------------------------------------

    def test_exception_on_required_filenames_has_empty_string(self):
        with self.assertRaises(ValidationError):
            Project.objects.create(
                name=self.PROJECT_NAME, semester=self.semester,
                required_student_files=["spam.cpp", ""])

    # -------------------------------------------------------------------------

    def test_exception_on_required_filename_has_illegal_path_chars(self):
        with self.assertRaises(ValidationError):
            Project.objects.create(
                name=self.PROJECT_NAME, semester=self.semester,
                required_student_files=["spam.cpp", "../spam.txt"])

    # -------------------------------------------------------------------------

    def test_exception_on_required_filename_has_illegal_shell_chars(self):
        with self.assertRaises(ValidationError):
            Project.objects.create(
                name=self.PROJECT_NAME, semester=self.semester,
                required_student_files=[
                    "spam.cpp", _FILENAME_WITH_SHELL_CHARS])

    # -------------------------------------------------------------------------

    def test_exception_on_negative_min_matches_in_expected_file_pattern(self):
        with self.assertRaises(ValidationError):
            Project.objects.create(
                name=self.PROJECT_NAME, semester=self.semester,
                expected_student_file_patterns={"spam": [-2, 4]})

    # -------------------------------------------------------------------------

    def test_exception_on_negative_max_matches_in_expected_file_pattern(self):
        with self.assertRaises(ValidationError):
            Project.objects.create(
                name=self.PROJECT_NAME, semester=self.semester,
                expected_student_file_patterns={"spam": [4, -2]})

    # -------------------------------------------------------------------------

    def test_exception_on_max_less_than_min_in_expected_file_pattern(self):
        with self.assertRaises(ValidationError):
            Project.objects.create(
                name=self.PROJECT_NAME, semester=self.semester,
                expected_student_file_patterns={"spam": [4, 1]})

    # -------------------------------------------------------------------------

    def test_exception_on_expected_file_patterns_has_empty_string(self):
        with self.assertRaises(ValidationError):
            Project.objects.create(
                name=self.PROJECT_NAME, semester=self.semester,
                expected_student_file_patterns={
                    "spam.cpp": [1, 2], "": [1, 2]})

    # -------------------------------------------------------------------------

    def test_exception_on_expected_file_patterns_has_illegal_path_chars(self):
        with self.assertRaises(ValidationError):
            Project.objects.create(
                name=self.PROJECT_NAME, semester=self.semester,
                expected_student_file_patterns={
                    "spam.cpp": [1, 2], "../test_*.cpp": [1, 2]})

    # -------------------------------------------------------------------------

    def test_exception_on_expected_file_patterns_has_illegal_shell_chars(self):
        with self.assertRaises(ValidationError):
            Project.objects.create(
                name=self.PROJECT_NAME, semester=self.semester,
                expected_student_file_patterns={
                    "spam.cpp": [1, 2], "spam[0-9]_; echo 'blah';": [1, 2]})


# -----------------------------------------------------------------------------
# -----------------------------------------------------------------------------

class ProjectFilesystemTest(TemporaryFilesystemTestCase):
    def setUp(self):
        super().setUp()
        self.course = Course.objects.create(name='eecs280')
        self.semester = Semester.objects.create(name='f15', course=self.course)
        self.PROJECT_NAME = 'stats_project'

        self.sample_project_filename = "spam_EGGS-42.txt"
        self.sample_project_file_contents = "spam egg sausage spam"

    # -------------------------------------------------------------------------
    # -------------------------------------------------------------------------

    def test_project_root_dir_created(self):
        project = Project(name=self.PROJECT_NAME, semester=self.semester)
        expected_project_root_dir = ut.get_project_root_dir(project)

        self.assertFalse(os.path.exists(expected_project_root_dir))

        project.save()

        self.assertTrue(os.path.isdir(expected_project_root_dir))

    # -------------------------------------------------------------------------

    def test_project_files_dir_created(self):
        project = Project(name=self.PROJECT_NAME, semester=self.semester)
        expected_project_files_dir = ut.get_project_files_dir(project)

        self.assertFalse(os.path.exists(expected_project_files_dir))

        project.save()

        self.assertTrue(os.path.isdir(expected_project_files_dir))

    # -------------------------------------------------------------------------

    def test_project_submissions_dir_created(self):
        project = Project(name=self.PROJECT_NAME, semester=self.semester)
        expected_project_submissions_by_student_dir = (
            ut.get_project_submissions_by_student_dir(project))

        self.assertFalse(
            os.path.exists(expected_project_submissions_by_student_dir))

        project.save()

        self.assertTrue(
            os.path.isdir(expected_project_submissions_by_student_dir))

    # -------------------------------------------------------------------------

    def test_valid_add_project_file(self):
        project = Project.objects.create(
            name=self.PROJECT_NAME, semester=self.semester)

        self.assertEqual(project.project_files, [])

        project.add_project_file(
            self.sample_project_filename, self.sample_project_file_contents)

        self.assertEqual(
            [self.sample_project_filename], project.project_files)

        with ut.ChangeDirectory(ut.get_project_files_dir(project)):
            self.assertTrue(os.path.isfile(self.sample_project_filename))
            with open(self.sample_project_filename) as f:
                self.assertEqual(self.sample_project_file_contents, f.read())

    # -------------------------------------------------------------------------

    def test_exception_on_add_file_overwrite_not_ok(self):
        project = Project.objects.create(
            name=self.PROJECT_NAME, semester=self.semester)

        project.add_project_file(
            self.sample_project_filename, self.sample_project_file_contents)

        with self.assertRaises(FileExistsError):
            project.add_project_file(
                self.sample_project_filename,
                self.sample_project_file_contents)

    # -------------------------------------------------------------------------

    def test_no_exception_on_add_file_overwrite_ok(self):
        project = Project.objects.create(
            name=self.PROJECT_NAME, semester=self.semester)

        self.assertEqual(project.project_files, [])

        project.add_project_file(
            self.sample_project_filename, self.sample_project_file_contents)

        new_contents = "cheeeeeeeeese"
        project.add_project_file(
            self.sample_project_filename, new_contents, overwrite_ok=True)

        with ut.ChangeDirectory(ut.get_project_files_dir(project)):
            self.assertTrue(os.path.isfile(self.sample_project_filename))
            with open(self.sample_project_filename) as f:
                self.assertEqual(new_contents, f.read())

    # -------------------------------------------------------------------------

    def test_exception_on_add_file_filename_that_is_path(self):
        # This test makes sure that add_project_file() doesn't allow
        # the user to add files in subdirectories (or worse, somewhere else
        # in the filesystem).
        project = Project.objects.create(
            name=self.PROJECT_NAME, semester=self.semester)
        with self.assertRaises(ValidationError):
            project.add_project_file(
                '../cheese.txt', "haxorz!", overwrite_ok=True)

    # -------------------------------------------------------------------------

    def test_exception_on_filename_that_has_shell_characters(self):
        project = Project.objects.create(
            name=self.PROJECT_NAME, semester=self.semester)
        with self.assertRaises(ValidationError):
            project.add_project_file(
                _FILENAME_WITH_SHELL_CHARS, "haxorz!", overwrite_ok=True)

    # -------------------------------------------------------------------------

    def test_exception_on_empty_filename(self):
        project = Project.objects.create(
            name=self.PROJECT_NAME, semester=self.semester)
        with self.assertRaises(ValidationError):
            project.add_project_file(
                "", self.sample_project_file_contents)

    # -------------------------------------------------------------------------

    def test_valid_remove_project_file(self):
        project = Project.objects.create(
            name=self.PROJECT_NAME, semester=self.semester)
        project.add_project_file(
            self.sample_project_filename, self.sample_project_file_contents)

        with ut.ChangeDirectory(ut.get_project_files_dir(project)):
            self.assertTrue(os.path.isfile(self.sample_project_filename))

        project.remove_project_file(self.sample_project_filename)
        with ut.ChangeDirectory(ut.get_project_files_dir(project)):
            self.assertFalse(os.path.isfile(self.sample_project_filename))

    # -------------------------------------------------------------------------

    def test_exception_on_remove_nonexistant_project_file(self):
        project = Project.objects.create(
            name=self.PROJECT_NAME, semester=self.semester)
        with self.assertRaises(FileNotFoundError):
            project.remove_project_file(self.sample_project_filename)
