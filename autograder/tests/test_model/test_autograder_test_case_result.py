from autograder.tests.temporary_filesystem_test_case import (
    TemporaryFilesystemTestCase)

from autograder.models import (
    Project, Semester, Course, AutograderTestCaseBase,
    CompiledAutograderTestCase, AutograderTestCaseResultBase)


class AutograderTestCaseResultTestCase(TemporaryFilesystemTestCase):
    def setUp(self):
        super().setUp()

        self.course = Course.objects.create(name='eecs280')
        self.semester = Semester.objects.create(name='f15', course=self.course)

        self.project = Project.objects.create(
            name='my_project', semester=self.semester,
            required_student_files=['file1.cpp', 'file2.cpp'],
            expected_student_file_patterns={'test_*.cpp': (1, 2)})

        self.project.add_project_file('spam.txt', 'hello there!')

        self.TEST_NAME = 'my_test'

        self.test_case = AutograderTestCaseBase.objects.create(
            name=self.TEST_NAME, project=self.project)

    # -------------------------------------------------------------------------

    def test_default_init(self):
        result = AutograderTestCaseResultBase.objects.create(
            test_case=self.test_case)

        loaded_result = AutograderTestCaseResultBase.objects.filter(
            test_case=self.test_case)[0]

        self.assertEqual(result, loaded_result)

        self.assertEqual(loaded_result.test_case, self.test_case)
        self.assertIsNone(loaded_result.return_code)
        self.assertEqual(loaded_result.standard_output, '')
        self.assertEqual(loaded_result.standard_error_output, '')
        self.assertFalse(loaded_result.timed_out)
        # self.assertIsNone(loaded_result.time_elapsed)
        self.assertIsNone(loaded_result.valgrind_return_code)
        self.assertEqual(loaded_result.valgrind_output, '')
        self.assertIsNone(loaded_result.compilation_return_code)
        self.assertEqual(loaded_result.compilation_standard_output, '')
        self.assertEqual(loaded_result.compilation_standard_error_output, '')
