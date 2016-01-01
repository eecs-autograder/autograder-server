from django.core.files.uploadedfile import SimpleUploadedFile
from django.core.exceptions import ValidationError

from autograder.core.models import Project
# AutograderTestCaseBase, AutograderTestCaseFactory)

import autograder.core.shared.global_constants as gc
import autograder.core.shared.feedback_configuration as fbc

import autograder.core.tests.dummy_object_utils as obj_ut
from autograder.core.tests.temporary_filesystem_test_case import (
    TemporaryFilesystemTestCase)

from .models import _DummyStudentTestSuite


class SharedSetUp:
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


class StudentTestSuiteBaseTestCase(SharedSetUp, TemporaryFilesystemTestCase):
    def test_valid_initialization_with_defaults(self):
        suite = _DummyStudentTestSuite.objects.validate_and_create(
            name=self.suite_name,
            project=self.project,
            student_test_case_filename_pattern=self.test_file_pattern.pattern,
            correct_implementation_filename=self.correct_impl_file.name)

        loaded = _DummyStudentTestSuite.objects.get(pk=suite.pk)

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
        self.assertEqual(0, loaded.points_per_buggy_implementation_exposed)

        self.assertEqual(
            fbc.StudentTestSuiteFeedbackConfiguration(),
            loaded.feedback_configuration)
        self.assertIsNone(
            loaded.post_deadline_final_submission_feedback_configuration)

    def test_valid_initialization_custom_values(self):
        implementation_file_alias = 'aliuuuus.h'
        time_limit = 11

        suite = _DummyStudentTestSuite.objects.validate_and_create(
            name=self.suite_name,
            project=self.project,
            student_test_case_filename_pattern=self.test_file_pattern.pattern,
            correct_implementation_filename=self.correct_impl_file.name,
            buggy_implementation_filenames=self.buggy_implementation_filenames,
            implementation_file_alias=implementation_file_alias,
            suite_resource_filenames=self.project_filenames,
            time_limit=time_limit,
            hide_from_students=False,
            points_per_buggy_implementation_exposed=1,
            feedback_configuration=(
                fbc.StudentTestSuiteFeedbackConfiguration.get_max_feedback()),
            post_deadline_final_submission_feedback_configuration=(
                fbc.StudentTestSuiteFeedbackConfiguration.get_max_feedback()),
        )

        loaded = _DummyStudentTestSuite.objects.get(pk=suite.pk)

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
        self.assertEqual(1, loaded.points_per_buggy_implementation_exposed)

        self.assertEqual(
            fbc.StudentTestSuiteFeedbackConfiguration.get_max_feedback(),
            loaded.feedback_configuration)
        self.assertEqual(
            fbc.StudentTestSuiteFeedbackConfiguration.get_max_feedback(),
            loaded.post_deadline_final_submission_feedback_configuration)

    def test_exception_on_non_unique_name_within_project(self):
        _DummyStudentTestSuite.objects.validate_and_create(
            name=self.suite_name,
            project=self.project,
            student_test_case_filename_pattern=self.test_file_pattern.pattern,
            correct_implementation_filename=self.correct_impl_file.name)

        with self.assertRaises(ValidationError):
            _DummyStudentTestSuite.objects.validate_and_create(
                name=self.suite_name,
                project=self.project,
                student_test_case_filename_pattern=self.test_file_pattern.pattern,
                correct_implementation_filename=self.correct_impl_file.name)

    def test_no_exception_same_name_different_project(self):
        suite = _DummyStudentTestSuite.objects.validate_and_create(
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

        loaded = _DummyStudentTestSuite.objects.get(pk=suite.pk)

        self.assertEqual(new_project, loaded.project)

    def test_exception_on_empty_name(self):
        with self.assertRaises(ValidationError) as cm:
            _DummyStudentTestSuite.objects.validate_and_create(
                name='',
                project=self.project,
                student_test_case_filename_pattern=self.test_file_pattern.pattern,
                correct_implementation_filename=self.correct_impl_file.name)

        self.assertTrue('name' in cm.exception.message_dict)

    def test_exception_on_null_name(self):
        with self.assertRaises(ValidationError) as cm:
            _DummyStudentTestSuite.objects.validate_and_create(
                name=None,
                project=self.project,
                student_test_case_filename_pattern=self.test_file_pattern.pattern,
                correct_implementation_filename=self.correct_impl_file.name)

        self.assertTrue('name' in cm.exception.message_dict)

    def test_name_whitespace_stripped(self):
        expected_name = 'eecs280'
        suite = _DummyStudentTestSuite.objects.validate_and_create(
            name='     ' + expected_name + '          ',
            project=self.project,
            student_test_case_filename_pattern=self.test_file_pattern.pattern,
            correct_implementation_filename=self.correct_impl_file.name)

        loaded = _DummyStudentTestSuite.objects.get(pk=suite.pk)
        self.assertEqual(expected_name, loaded.name)

    def test_exception_on_name_only_whitespace(self):
        with self.assertRaises(ValidationError) as cm:
            _DummyStudentTestSuite.objects.validate_and_create(
                name='        ',
                project=self.project,
                student_test_case_filename_pattern=self.test_file_pattern.pattern,
                correct_implementation_filename=self.correct_impl_file.name)

        self.assertTrue('name' in cm.exception.message_dict)

    # -------------------------------------------------------------------------

    def test_invalid_characters_in_implementation_file_alias(self):
        for bad_filename in ('; echo "haxorz" #', '..', '.spam'):
            with self.assertRaises(ValidationError) as cm:
                _DummyStudentTestSuite.objects.validate_and_create(
                    name='spam',
                    project=self.project,
                    student_test_case_filename_pattern=self.test_file_pattern.pattern,
                    correct_implementation_filename=self.correct_impl_file.name,
                    implementation_file_alias=bad_filename)

            self.assertTrue(
                'implementation_file_alias' in cm.exception.message_dict)

    # -------------------------------------------------------------------------

    def test_exception_student_test_case_filename_pattern_not_in_project_expected_student_files(self):
        with self.assertRaises(ValidationError) as cm:
            _DummyStudentTestSuite.objects.validate_and_create(
                name=self.suite_name,
                project=self.project,
                student_test_case_filename_pattern=['not_a_pattern*.cpp'],
                correct_implementation_filename=self.correct_impl_file.name)

        self.assertTrue(
            'student_test_case_filename_pattern' in cm.exception.message_dict)

    def test_exception_correct_implementation_filename_not_project_file(self):
        with self.assertRaises(ValidationError) as cm:
            _DummyStudentTestSuite.objects.validate_and_create(
                name=self.suite_name,
                project=self.project,
                student_test_case_filename_pattern=self.test_file_pattern.pattern,
                correct_implementation_filename='not_a_project_file')

        self.assertTrue(
            'correct_implementation_filename' in cm.exception.message_dict)

    def test_exception_some_buggy_implementation_filenames_not_project_files(self):
        with self.assertRaises(ValidationError) as cm:
            _DummyStudentTestSuite.objects.validate_and_create(
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
            _DummyStudentTestSuite.objects.validate_and_create(
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
            _DummyStudentTestSuite.objects.validate_and_create(
                name=self.suite_name,
                project=self.project,
                student_test_case_filename_pattern=self.test_file_pattern.pattern,
                correct_implementation_filename=self.correct_impl_file.name,
                time_limit=0)

        self.assertTrue('time_limit' in cm.exception.message_dict)

        with self.assertRaises(ValidationError) as cm:
            _DummyStudentTestSuite.objects.validate_and_create(
                name=self.suite_name,
                project=self.project,
                student_test_case_filename_pattern=self.test_file_pattern.pattern,
                correct_implementation_filename=self.correct_impl_file.name,
                time_limit=61)

        self.assertTrue('time_limit' in cm.exception.message_dict)
