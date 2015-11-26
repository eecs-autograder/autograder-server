from django.core.files.uploadedfile import SimpleUploadedFile
from django.core.exceptions import ValidationError

from autograder.models import (
    Project, Semester, Course, StudentTestSuiteBase, StudentTestSuiteFactory)
# AutograderTestCaseBase, AutograderTestCaseFactory)

import autograder.shared.global_constants as gc


class StudentTestSuiteBaseTests(object):
    """
    These test cases need to be run on all classes that inherit from
    autograder.models.StudentTestSuite. In order to accomplish this,
    the test fixture dedicated to that class should inherit FIRST from this
    class, followed by django.test.TestCase (or a derived class thereof).
    Then, that test fixture should override the
    get_student_test_suite_type_str_for_factory() method from this class.
    """
    @classmethod
    def setUpClass(class_):
        super().setUpClass()

        class_.buggy_implementation_files = [
            SimpleUploadedFile('buggy1.cpp', b'hello there!'),
            SimpleUploadedFile('buggy2.cpp', b'egg bacon spam and sausage'),
        ]

        class_.buggy_implementation_filenames = [
            file_.name for file_ in class_.buggy_implementation_files]

        class_.project_files = [
            SimpleUploadedFile('spam.cpp', b'hello there!'),
            SimpleUploadedFile('eggs.cpp', b'egg bacon spam and sausage'),
        ]

        class_.project_filenames = [
            file_.name for file_ in class_.project_files]

    def setUp(self):
        super().setUp()

        course = Course.objects.validate_and_create(name='eecs280')
        semester = Semester.objects.validate_and_create(
            name='f15', course=course)

        self.test_file_pattern = Project.FilePatternTuple('test_*.cpp', 1, 2)
        self.project = Project.objects.validate_and_create(
            name='my_project', semester=semester,
            expected_student_file_patterns=[self.test_file_pattern]
        )

        for file_obj in self.project_files:
            self.project.add_project_file(file_obj)

        for file_obj in self.buggy_implementation_files:
            self.project.add_project_file(file_obj)

        self.correct_impl_file = SimpleUploadedFile(
            'correct_impl.cpp', b'spam egg sausage')
        self.project.add_project_file(self.correct_impl_file)

        self.suite_name = 'my_test'

    # -------------------------------------------------------------------------

    def get_student_test_suite_type_str_for_factory(self):
        raise NotImplementedError(
            "This method must be overridden in derived test fixtures")

    # -------------------------------------------------------------------------

    def test_valid_initialization_with_defaults(self):
        suite = StudentTestSuiteFactory.validate_and_create(
            self.get_student_test_suite_type_str_for_factory(),
            name=self.suite_name,
            project=self.project,
            student_test_case_filename_pattern=self.test_file_pattern.pattern,
            correct_implementation_filename=self.correct_impl_file.name)

        loaded = StudentTestSuiteBase.objects.get(pk=suite.pk)

        self.assertEqual(self.suite_name, loaded.name)
        self.assertEqual(self.project, loaded.project)
        self.assertEqual(
            self.test_file_pattern.pattern,
            loaded.student_test_case_filename_pattern)
        self.assertEqual(
            self.correct_impl_file.name,
            loaded.correct_implementation_filename
        )

        self.assertEqual([], loaded.buggy_implementation_filenames)
        self.assertEqual('', loaded.implementation_file_alias)
        self.assertEqual([], loaded.suite_resource_filenames)
        self.assertEqual(gc.DEFAULT_SUBPROCESS_TIMEOUT, loaded.time_limit)
        self.assertTrue(loaded.hide_from_students)

    def test_valid_initialization_custom_values(self):
        implementation_file_alias = 'aliuuuus.h'
        time_limit = 11

        suite = StudentTestSuiteFactory.validate_and_create(
            self.get_student_test_suite_type_str_for_factory(),
            name=self.suite_name,
            project=self.project,
            student_test_case_filename_pattern=self.test_file_pattern.pattern,
            correct_implementation_filename=self.correct_impl_file.name,
            buggy_implementation_filenames=self.buggy_implementation_filenames,
            implementation_file_alias=implementation_file_alias,
            suite_resource_filenames=self.project_files,
            time_limit=time_limit,
            hide_from_students=False
        )

        loaded = StudentTestSuiteBase.objects.get(pk=suite.pk)

        self.assertEqual(self.suite_name, loaded.name)
        self.assertEqual(self.project, loaded.project)
        self.assertEqual(
            self.test_file_pattern.pattern,
            loaded.student_test_case_filename_pattern)
        self.assertEqual(
            self.correct_impl_file.name,
            loaded.correct_implementation_filename
        )

        self.assertEqual(
            self.buggy_implementation_filenames,
            loaded.buggy_implementation_filenames)
        self.assertEqual(
            implementation_file_alias, loaded.implementation_file_alias)
        self.assertEqual(
            self.project_filenames, loaded.suite_resource_filenames)
        self.assertEqual(time_limit, loaded.time_limit)
        self.assertFalse(loaded.hide_from_students)

    def test_exception_on_non_unique_name_within_project(self):
        self.fail()

    def test_no_exception_same_name_different_project(self):
        self.fail()

    def test_no_exception_same_name_and_project_name_different_semester(self):
        self.fail()

    def test_no_exception_same_name_project_name_and_semester_name_different_course(self):
        self.fail()

    def test_exception_on_empty_name(self):
        self.fail()

    def test_exception_on_null_name(self):
        self.fail()

    def test_name_whitespace_stripped(self):
        self.fail()

    def test_exception_on_name_only_whitespace(self):
        self.fail()

    # -------------------------------------------------------------------------

    def test_exception_student_test_case_filename_pattern_not_in_project_expected_student_files(self):
        self.fail()

    def test_exception_correct_implementation_filename_not_project_file(self):
        self.fail()

    def test_exception_some_buggy_implementation_filenames_not_project_files(self):
        self.fail()

    # -------------------------------------------------------------------------

    def test_exception_implementation_file_alias_is_path(self):
        self.fail()

    def test_exception_implementation_file_alias_has_shell_chars(self):
        self.fail()

    def test_exception_implementation_file_alias_is_dot(self):
        self.fail()

    def test_exception_implementation_file_alias_starts_with_dot(self):
        self.fail()

    # -------------------------------------------------------------------------

    def test_exception_some_suite_resource_filenames_not_project_files(self):
        self.fail()

    def test_exception_time_limit_out_of_bounds(self):
        self.fail()
