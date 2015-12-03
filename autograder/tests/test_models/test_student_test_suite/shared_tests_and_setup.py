from django.core.files.uploadedfile import SimpleUploadedFile
from django.core.exceptions import ValidationError

from autograder.models import (
    Project, Semester, Course, StudentTestSuiteBase, StudentTestSuiteFactory)
# AutograderTestCaseBase, AutograderTestCaseFactory)

import autograder.shared.global_constants as gc

import autograder.tests.dummy_object_utils as obj_ut


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

        self.course = obj_ut.create_dummy_courses()
        self.semester = obj_ut.create_dummy_semesters(self.course)

        self.test_file_pattern = Project.FilePatternTuple('test_*.cpp', 1, 2)
        self.project = Project.objects.validate_and_create(
            name='my_project', semester=self.semester,
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

        # Fat interface fields
        self.assertEqual('g++', loaded.compiler)
        self.assertEqual([], loaded.compiler_flags)
        self.assertEqual([], loaded.suite_resource_files_to_compile_together)

    def test_valid_initialization_custom_values(self):
        implementation_file_alias = 'aliuuuus.h'
        time_limit = 11
        compiler_flags = ['-Wall', '-Werror', '-pedantic']

        suite = StudentTestSuiteFactory.validate_and_create(
            self.get_student_test_suite_type_str_for_factory(),
            name=self.suite_name,
            project=self.project,
            student_test_case_filename_pattern=self.test_file_pattern.pattern,
            correct_implementation_filename=self.correct_impl_file.name,
            buggy_implementation_filenames=self.buggy_implementation_filenames,
            implementation_file_alias=implementation_file_alias,
            suite_resource_filenames=self.project_filenames,
            time_limit=time_limit,
            hide_from_students=False,

            compiler='g++',
            compiler_flags=compiler_flags,
            suite_resource_files_to_compile_together=self.project_filenames
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

        self.assertEqual(compiler_flags, loaded.compiler_flags)
        self.assertEqual(
            self.project_filenames,
            loaded.suite_resource_files_to_compile_together)

    def test_exception_on_non_unique_name_within_project(self):
        StudentTestSuiteFactory.validate_and_create(
            self.get_student_test_suite_type_str_for_factory(),
            name=self.suite_name,
            project=self.project,
            student_test_case_filename_pattern=self.test_file_pattern.pattern,
            correct_implementation_filename=self.correct_impl_file.name)

        with self.assertRaises(ValidationError):
            StudentTestSuiteFactory.validate_and_create(
                self.get_student_test_suite_type_str_for_factory(),
                name=self.suite_name,
                project=self.project,
                student_test_case_filename_pattern=self.test_file_pattern.pattern,
                correct_implementation_filename=self.correct_impl_file.name)

    def test_no_exception_same_name_different_project(self):
        suite = StudentTestSuiteFactory.validate_and_create(
            self.get_student_test_suite_type_str_for_factory(),
            name=self.suite_name,
            project=self.project,
            student_test_case_filename_pattern=self.test_file_pattern.pattern,
            correct_implementation_filename=self.correct_impl_file.name)

        new_project = self.project
        new_project.pk = None
        new_project.name = "other_project"
        new_project.validate_and_save()
        new_project.add_project_file(self.correct_impl_file)

        suite.pk = None
        suite.project = new_project

        suite.validate_and_save()

        loaded = StudentTestSuiteBase.objects.get(pk=suite.pk)

        self.assertEqual(new_project, loaded.project)

    def test_exception_on_empty_name(self):
        with self.assertRaises(ValidationError) as cm:
            StudentTestSuiteFactory.validate_and_create(
                self.get_student_test_suite_type_str_for_factory(),
                name='',
                project=self.project,
                student_test_case_filename_pattern=self.test_file_pattern.pattern,
                correct_implementation_filename=self.correct_impl_file.name)

        self.assertTrue('name' in cm.exception.message_dict)

    def test_exception_on_null_name(self):
        with self.assertRaises(ValidationError) as cm:
            StudentTestSuiteFactory.validate_and_create(
                self.get_student_test_suite_type_str_for_factory(),
                name=None,
                project=self.project,
                student_test_case_filename_pattern=self.test_file_pattern.pattern,
                correct_implementation_filename=self.correct_impl_file.name)

        self.assertTrue('name' in cm.exception.message_dict)

    def test_name_whitespace_stripped(self):
        expected_name = 'eecs280'
        suite = StudentTestSuiteFactory.validate_and_create(
            self.get_student_test_suite_type_str_for_factory(),
            name='     ' + expected_name + '          ',
            project=self.project,
            student_test_case_filename_pattern=self.test_file_pattern.pattern,
            correct_implementation_filename=self.correct_impl_file.name)

        loaded = StudentTestSuiteBase.objects.get(pk=suite.pk)
        self.assertEqual(expected_name, loaded.name)

    def test_exception_on_name_only_whitespace(self):
        with self.assertRaises(ValidationError) as cm:
            StudentTestSuiteFactory.validate_and_create(
                self.get_student_test_suite_type_str_for_factory(),
                name='        ',
                project=self.project,
                student_test_case_filename_pattern=self.test_file_pattern.pattern,
                correct_implementation_filename=self.correct_impl_file.name)

        self.assertTrue('name' in cm.exception.message_dict)

    # -------------------------------------------------------------------------

    def test_exception_student_test_case_filename_pattern_not_in_project_expected_student_files(self):
        with self.assertRaises(ValidationError) as cm:
            StudentTestSuiteFactory.validate_and_create(
                self.get_student_test_suite_type_str_for_factory(),
                name=self.suite_name,
                project=self.project,
                student_test_case_filename_pattern=['not_a_pattern*.cpp'],
                correct_implementation_filename=self.correct_impl_file.name)

        self.assertTrue(
            'student_test_case_filename_pattern' in cm.exception.message_dict)

    def test_exception_correct_implementation_filename_not_project_file(self):
        with self.assertRaises(ValidationError) as cm:
            StudentTestSuiteFactory.validate_and_create(
                self.get_student_test_suite_type_str_for_factory(),
                name=self.suite_name,
                project=self.project,
                student_test_case_filename_pattern=self.test_file_pattern.pattern,
                correct_implementation_filename='not_a_project_file')

        self.assertTrue(
            'correct_implementation_filename' in cm.exception.message_dict)

    def test_exception_some_buggy_implementation_filenames_not_project_files(self):
        with self.assertRaises(ValidationError) as cm:
            StudentTestSuiteFactory.validate_and_create(
                self.get_student_test_suite_type_str_for_factory(),
                name='',
                project=self.project,
                student_test_case_filename_pattern=self.test_file_pattern.pattern,
                correct_implementation_filename=self.correct_impl_file.name,
                buggy_implementation_filenames=[
                    self.project_filenames[0], 'not_a_project_file'])

        self.assertTrue(
            'buggy_implementation_filenames' in cm.exception.message_dict)

    # -------------------------------------------------------------------------

    def test_exception_some_suite_resource_filenames_not_project_files(self):
        with self.assertRaises(ValidationError) as cm:
            StudentTestSuiteFactory.validate_and_create(
                self.get_student_test_suite_type_str_for_factory(),
                name='',
                project=self.project,
                student_test_case_filename_pattern=self.test_file_pattern.pattern,
                correct_implementation_filename=self.correct_impl_file.name,
                suite_resource_filenames=[
                    self.project_filenames[0], 'not_a_project_file'])

        self.assertTrue(
            'suite_resource_filenames' in cm.exception.message_dict)

    def test_exception_time_limit_out_of_bounds(self):
        with self.assertRaises(ValidationError) as cm:
            StudentTestSuiteFactory.validate_and_create(
                self.get_student_test_suite_type_str_for_factory(),
                name=self.suite_name,
                project=self.project,
                student_test_case_filename_pattern=self.test_file_pattern.pattern,
                correct_implementation_filename=self.correct_impl_file.name,
                time_limit=0)

        self.assertTrue('time_limit' in cm.exception.message_dict)

        with self.assertRaises(ValidationError) as cm:
            StudentTestSuiteFactory.validate_and_create(
                self.get_student_test_suite_type_str_for_factory(),
                name=self.suite_name,
                project=self.project,
                student_test_case_filename_pattern=self.test_file_pattern.pattern,
                correct_implementation_filename=self.correct_impl_file.name,
                time_limit=61)

        self.assertTrue('time_limit' in cm.exception.message_dict)

    # -------------------------------------------------------------------------

    def test_exception_invalid_compiler(self):
        with self.assertRaises(ValidationError) as cm:
            StudentTestSuiteFactory.validate_and_create(
                self.get_student_test_suite_type_str_for_factory(),
                name=self.suite_name,
                project=self.project,
                student_test_case_filename_pattern=self.test_file_pattern.pattern,
                correct_implementation_filename=self.correct_impl_file.name,
                compiler='not_a_compiler++')

        self.assertTrue('compiler' in cm.exception.message_dict)

    def test_exception_invalid_characters_in_compiler_flags(self):
        with self.assertRaises(ValidationError) as cm:
            StudentTestSuiteFactory.validate_and_create(
                self.get_student_test_suite_type_str_for_factory(),
                name=self.suite_name,
                project=self.project,
                student_test_case_filename_pattern=self.test_file_pattern.pattern,
                correct_implementation_filename=self.correct_impl_file.name,
                compiler_flags=['-Wall', ';echo "haxorz" #'])

        self.assertTrue('compiler_flags' in cm.exception.message_dict)

        error_list = cm.exception.message_dict['compiler_flags']
        self.assertEqual('', error_list[0])
        self.assertTrue(error_list[1])

    def test_exception_compiler_flag_is_whitespace(self):
        with self.assertRaises(ValidationError) as cm:
            StudentTestSuiteFactory.validate_and_create(
                self.get_student_test_suite_type_str_for_factory(),
                name=self.suite_name,
                project=self.project,
                student_test_case_filename_pattern=self.test_file_pattern.pattern,
                correct_implementation_filename=self.correct_impl_file.name,
                compiler_flags=['-Wall', '          '])

        self.assertTrue('compiler_flags' in cm.exception.message_dict)

    def test_exception_some_suite_resource_files_to_compile_together_not_suite_resource_files(self):
        suite_resource_filenames = self.project_filenames[:1]
        with self.assertRaises(ValidationError) as cm:
            StudentTestSuiteFactory.validate_and_create(
                self.get_student_test_suite_type_str_for_factory(),
                name=self.suite_name,
                project=self.project,
                student_test_case_filename_pattern=self.test_file_pattern.pattern,
                suite_resource_filenames=suite_resource_filenames,
                correct_implementation_filename=self.correct_impl_file.name,
                suite_resource_files_to_compile_together=(
                    suite_resource_filenames + ['not_a_suite_resource_file']))

        self.assertTrue('suite_resource_files_to_compile_together'
                        in cm.exception.message_dict)
