import os
import datetime

from django.core.exceptions import ValidationError
from django.utils import timezone

from autograder.models import Project, Semester, Course

import autograder.shared.utilities as ut

from autograder.tests.temporary_filesystem_test_case import (
    TemporaryFilesystemTestCase)

# note to self: ctor for SimpleUploadedFile takes (filename, contents).
#               contents must be binary data
from django.core.files.uploadedfile import SimpleUploadedFile


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
        new_project = Project.objects.validate_and_create(
            name=self.PROJECT_NAME, semester=self.semester)

        loaded_project = Project.objects.get(
            name=self.PROJECT_NAME, semester=self.semester)

        self.assertEqual(loaded_project, new_project)
        self.assertEqual(loaded_project.name, new_project.name)
        self.assertEqual(loaded_project.semester, new_project.semester)

        self.assertEqual(list(loaded_project.project_files.all()), [])
        self.assertEqual(loaded_project.visible_to_students, False)
        self.assertEqual(loaded_project.closing_time, None)
        self.assertEqual(loaded_project.disallow_student_submissions, False)
        self.assertEqual(loaded_project.min_group_size, 1)
        self.assertEqual(loaded_project.max_group_size, 1)
        self.assertEqual(loaded_project.required_student_files, [])
        self.assertEqual(
            list(loaded_project.expected_student_file_patterns.all()), [])

    # -------------------------------------------------------------------------

    def test_valid_create_non_defaults(self):
        tomorrow_date = timezone.now() + datetime.timedelta(days=1)
        min_group_size = 2
        max_group_size = 5
        required_student_files = ["spam.cpp", "eggs.cpp"]
        expected_student_file_patterns = sorted((
            ("test_*.cpp", 1, 10),
            ("test[0-9].cpp", 2, 2),
            ("test[!0-9]?.cpp", 3, 5)
        ))

        new_project = Project.objects.validate_and_create(
            name=self.PROJECT_NAME,
            semester=self.semester,
            visible_to_students=True,
            closing_time=tomorrow_date,
            disallow_student_submissions=True,
            min_group_size=min_group_size,
            max_group_size=max_group_size,
            required_student_files=required_student_files,
            # expected_student_file_patterns=expected_student_file_patterns
        )

        for pattern, min_matches, max_matches in expected_student_file_patterns:
            new_project.add_expected_student_file_pattern(
                pattern, min_matches, max_matches)

        new_project.validate_and_save()

        loaded_project = Project.objects.get(
            name=self.PROJECT_NAME, semester=self.semester)

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

        iterable = zip(
            expected_student_file_patterns,
            sorted(loaded_project.get_expected_student_file_patterns()))

        for expected, actual in iterable:
            self.assertEqual(expected[0], actual.pattern)
            self.assertEqual(expected[1], actual.min_num_matches)
            self.assertEqual(expected[2], actual.max_num_matches)

    # -------------------------------------------------------------------------

    def test_exception_on_empty_name(self):
        with self.assertRaises(ValidationError) as cm:
            Project.objects.validate_and_create(
                name='', semester=self.semester)
        self.assertTrue('name' in cm.exception.message_dict)

    # -------------------------------------------------------------------------

    def test_exception_on_null_name(self):
        with self.assertRaises(ValidationError) as cm:
            Project.objects.validate_and_create(
                name=None, semester=self.semester)
        self.assertTrue('name' in cm.exception.message_dict)

    # -------------------------------------------------------------------------

    def test_exception_on_non_unique_name(self):
        Project.objects.validate_and_create(
            name=self.PROJECT_NAME, semester=self.semester)
        with self.assertRaises(ValidationError):
            Project.objects.validate_and_create(
                name=self.PROJECT_NAME, semester=self.semester)

    # -------------------------------------------------------------------------

    def test_no_exception_same_name_different_semester(self):
        new_semester_name = 'w16'
        new_semester = Semester.objects.validate_and_create(
            name=new_semester_name, course=self.course)

        Project.objects.validate_and_create(
            name=self.PROJECT_NAME, semester=self.semester)

        new_project = Project.objects.validate_and_create(
            name=self.PROJECT_NAME, semester=new_semester)

        loaded_new_project = Project.objects.get(
            name=self.PROJECT_NAME, semester=new_semester)

        self.assertEqual(loaded_new_project, new_project)
        self.assertEqual(loaded_new_project.name, new_project.name)
        self.assertEqual(loaded_new_project.semester, new_project.semester)

    # -------------------------------------------------------------------------

    def test_no_exception_same_semester_and_project_names_different_course(self):
        new_course_name = 'eecs381'
        new_course = Course.objects.validate_and_create(name=new_course_name)
        new_semester = Semester.objects.validate_and_create(
            name=self.semester.name, course=new_course)

        Project.objects.validate_and_create(
            name=self.PROJECT_NAME, semester=self.semester)
        new_project = Project.objects.validate_and_create(
            name=self.PROJECT_NAME, semester=new_semester)

        loaded_new_project = Project.objects.get(
            name=self.PROJECT_NAME, semester=new_semester)

        self.assertEqual(loaded_new_project, new_project)
        self.assertEqual(loaded_new_project.name, new_project.name)
        self.assertEqual(loaded_new_project.semester, new_project.semester)

        self.assertNotEqual(
            loaded_new_project.semester.course, self.course)

    # -------------------------------------------------------------------------

    def test_exception_on_min_group_size_too_small(self):
        with self.assertRaises(ValidationError) as cm:
            Project.objects.validate_and_create(
                name=self.PROJECT_NAME, semester=self.semester,
                min_group_size=0)
        self.assertTrue('min_group_size' in cm.exception.message_dict)

    # -------------------------------------------------------------------------

    def test_exception_on_max_group_size_too_small(self):
        with self.assertRaises(ValidationError) as cm:
            Project.objects.validate_and_create(
                name=self.PROJECT_NAME, semester=self.semester,
                max_group_size=0)
        self.assertTrue('max_group_size' in cm.exception.message_dict)

    # -------------------------------------------------------------------------

    def test_exception_on_max_group_size_smaller_than_min_group_size(self):
        with self.assertRaises(ValidationError) as cm:
            Project.objects.validate_and_create(
                name=self.PROJECT_NAME, semester=self.semester,
                min_group_size=3, max_group_size=2)
        self.assertTrue('max_group_size' in cm.exception.message_dict)

    # -------------------------------------------------------------------------

    def test_exception_on_required_filename_is_empty_string(self):
        with self.assertRaises(ValidationError) as cm:
            Project.objects.validate_and_create(
                name=self.PROJECT_NAME, semester=self.semester,
                required_student_files=['spam.cpp', ''])

        self.assertTrue('required_student_files' in cm.exception.message_dict)

        # Make sure that there is an error message only in the correct spot.
        self.assertEqual(
            '', cm.exception.message_dict['required_student_files'][0])
        self.assertTrue(cm.exception.message_dict['required_student_files'][1])

    # -------------------------------------------------------------------------

    def test_exception_on_required_filename_has_illegal_path_chars(self):
        with self.assertRaises(ValidationError) as cm:
            Project.objects.validate_and_create(
                name=self.PROJECT_NAME, semester=self.semester,
                required_student_files=['..', '../spam.txt'])
        self.assertTrue(cm.exception.message_dict['required_student_files'][0])
        self.assertTrue(cm.exception.message_dict['required_student_files'][1])

    # -------------------------------------------------------------------------

    def test_exception_on_required_filename_has_illegal_shell_chars(self):
        with self.assertRaises(ValidationError) as cm:
            Project.objects.validate_and_create(
                name=self.PROJECT_NAME, semester=self.semester,
                required_student_files=[_FILENAME_WITH_SHELL_CHARS])
        self.assertTrue(cm.exception.message_dict['required_student_files'][0])

    # -------------------------------------------------------------------------

    def test_exception_on_required_filename_starts_with_dot(self):
        with self.assertRaises(ValidationError) as cm:
            Project.objects.validate_and_create(
                name=self.PROJECT_NAME, semester=self.semester,
                required_student_files=['.spamspam'])
        self.assertTrue(cm.exception.message_dict['required_student_files'][0])

    # -------------------------------------------------------------------------

    def test_exception_on_negative_min_matches_in_expected_file_pattern(self):
        p = Project.objects.validate_and_create(
            name=self.PROJECT_NAME, semester=self.semester)

        with self.assertRaises(ValidationError):
            p.add_expected_student_file_pattern("spam_*.txt", -2, 4)

    # -------------------------------------------------------------------------

    def test_exception_on_negative_max_matches_in_expected_file_pattern(self):
        p = Project.objects.validate_and_create(
            name=self.PROJECT_NAME, semester=self.semester)

        with self.assertRaises(ValidationError):
            p.add_expected_student_file_pattern("spam_*.txt", 4, -2)

    # -------------------------------------------------------------------------

    def test_exception_on_max_less_than_min_in_expected_file_pattern(self):
        p = Project.objects.validate_and_create(
            name=self.PROJECT_NAME, semester=self.semester)

        with self.assertRaises(ValidationError):
            p.add_expected_student_file_pattern("spam_*.txt", 4, 1)

    # -------------------------------------------------------------------------

    def test_exception_on_expected_file_patterns_has_empty_string(self):
        p = Project.objects.validate_and_create(
            name=self.PROJECT_NAME, semester=self.semester)

        with self.assertRaises(ValidationError):
            p.add_expected_student_file_pattern("", 1, 2)

    # -------------------------------------------------------------------------

    def test_exception_on_expected_file_patterns_has_illegal_path_chars(self):
        p = Project.objects.validate_and_create(
            name=self.PROJECT_NAME, semester=self.semester)

        with self.assertRaises(ValidationError):
            p.add_expected_student_file_pattern("../test_*.cpp", 1, 2)

    # -------------------------------------------------------------------------

    def test_exception_on_expected_file_patterns_has_illegal_shell_chars(self):
        p = Project.objects.validate_and_create(
            name=self.PROJECT_NAME, semester=self.semester)

        with self.assertRaises(ValidationError):
            p.add_expected_student_file_pattern(
                "spam[0-9]_; echo 'blah';", 1, 2)


# -----------------------------------------------------------------------------
# -----------------------------------------------------------------------------

class ProjectFilesystemTest(TemporaryFilesystemTestCase):
    def setUp(self):
        super().setUp()
        self.course = Course.objects.create(name='eecs280')
        self.semester = Semester.objects.create(name='f15', course=self.course)
        self.PROJECT_NAME = 'stats_project'

        self.sample_project_filename = "spam_EGGS-42.txt"
        self.sample_project_file_contents = b"spam egg sausage spam"
        self.sample_project_file = SimpleUploadedFile(
            self.sample_project_filename, self.sample_project_file_contents)

    # -------------------------------------------------------------------------
    # -------------------------------------------------------------------------

    def test_project_root_dir_created_and_removed(self):
        project = Project(name=self.PROJECT_NAME, semester=self.semester)
        expected_project_root_dir = ut.get_project_root_dir(project)

        self.assertFalse(os.path.exists(expected_project_root_dir))

        project.save()
        self.assertTrue(os.path.isdir(expected_project_root_dir))

        project.delete()
        self.assertFalse(os.path.exists(expected_project_root_dir))

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
        project = Project.objects.validate_and_create(
            name=self.PROJECT_NAME, semester=self.semester)

        self.assertEqual(project.get_project_files(), [])

        project.add_project_file(self.sample_project_file)

        self.assertEqual(1, len(project.get_project_files()))
        uploaded_file = project.get_project_files()[0]

        self.assertEqual(
            os.path.basename(uploaded_file.name), self.sample_project_filename)
        self.assertEqual(
            uploaded_file.read(), self.sample_project_file_contents)

        with ut.ChangeDirectory(ut.get_project_files_dir(project)):
            self.assertTrue(os.path.isfile(self.sample_project_filename))

    # -------------------------------------------------------------------------

    # This test can probably be phased out.
    # def test_exception_on_add_file_overwrite_not_ok(self):
    #     project = Project.objects.create(
    #         name=self.PROJECT_NAME, semester=self.semester)

    #     project.add_project_file(
    #         self.sample_project_filename, self.sample_project_file_contents)

    #     with self.assertRaises(FileExistsError):
    #         project.add_project_file(
    #             self.sample_project_filename,
    #             self.sample_project_file_contents)

    # -------------------------------------------------------------------------

    # This test can probably be phased out.
#     def test_no_exception_on_add_file_overwrite_ok(self):
#         project = Project.objects.create(
#             name=self.PROJECT_NAME, semester=self.semester)

#         self.assertEqual(project.project_files, [])

#         project.add_project_file(
#             self.sample_project_filename, self.sample_project_file_contents)

#         new_contents = "cheeeeeeeeese"
#         project.add_project_file(
#             self.sample_project_filename, new_contents, overwrite_ok=True)

#         with ut.ChangeDirectory(ut.get_project_files_dir(project)):
#             self.assertTrue(os.path.isfile(self.sample_project_filename))
#             with open(self.sample_project_filename) as f:
#                 self.assertEqual(new_contents, f.read())

#     # -------------------------------------------------------------------------

    # This test can probably be phased out.
    # NOTE: Django's default storage system strips path information from
    # uploaded files
    # def test_exception_on_add_file_filename_that_is_path(self):
    #     # This test makes sure that add_project_file() doesn't allow
    #     # the user to add files in subdirectories (or worse, somewhere else
    #     # in the filesystem).
    #     project = Project.objects.validate_and_create(
    #         name=self.PROJECT_NAME, semester=self.semester)
    #     with self.assertRaises(ValidationError):
    #         project.add_project_file(
    #             SimpleUploadedFile('../spam/egg/cheese.txt', b"haxorz!"))

    #     with self.assertRaises(ValueError):
    #         project.add_project_file(
    #             SimpleUploadedFile('..', "haxorz!"))

    # -------------------------------------------------------------------------

    def test_exception_on_filename_that_has_shell_characters(self):
        project = Project.objects.validate_and_create(
            name=self.PROJECT_NAME, semester=self.semester)
        with self.assertRaises(ValidationError):
            project.add_project_file(
                SimpleUploadedFile(_FILENAME_WITH_SHELL_CHARS, b"haxorz!"))

    # -------------------------------------------------------------------------

    def test_exception_on_filename_that_starts_with_dot(self):
        project = Project.objects.validate_and_create(
            name=self.PROJECT_NAME, semester=self.semester)
        with self.assertRaises(ValidationError):
            project.add_project_file(
                SimpleUploadedFile('.cheese.txt', b"whoa!"))

    # -------------------------------------------------------------------------

    def test_exception_on_empty_filename(self):
        project = Project.objects.validate_and_create(
            name=self.PROJECT_NAME, semester=self.semester)
        with self.assertRaises(ValidationError):
            project.add_project_file(
                SimpleUploadedFile("", self.sample_project_file_contents))

    # -------------------------------------------------------------------------

    # This test can probably be phased out.
#     def test_valid_remove_project_file(self):
#         project = Project.objects.create(
#             name=self.PROJECT_NAME, semester=self.semester)
#         project.add_project_file(
#             self.sample_project_filename, self.sample_project_file_contents)

#         with ut.ChangeDirectory(ut.get_project_files_dir(project)):
#             self.assertTrue(os.path.isfile(self.sample_project_filename))

#         project.remove_project_file(self.sample_project_filename)
#         with ut.ChangeDirectory(ut.get_project_files_dir(project)):
#             self.assertFalse(os.path.isfile(self.sample_project_filename))

#     # -------------------------------------------------------------------------

    # This test can probably be phased out.
#     def test_exception_on_remove_nonexistant_project_file(self):
#         project = Project.objects.create(
#             name=self.PROJECT_NAME, semester=self.semester)
#         with self.assertRaises(FileNotFoundError):
#             project.remove_project_file(self.sample_project_filename)
