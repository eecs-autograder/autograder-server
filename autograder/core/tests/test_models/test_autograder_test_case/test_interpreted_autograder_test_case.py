import uuid
from django.core.files.uploadedfile import SimpleUploadedFile
from django.core.exceptions import ValidationError

from autograder.core.tests.temporary_filesystem_test_case import (
    TemporaryFilesystemTestCase)
from autograder.core.tests import dummy_object_utils as obj_ut
from autograder.security.autograder_sandbox import AutograderSandbox
import autograder.core.models as ag_models


class _SetUpBase:
    def setUp(self):
        super().setUp()

        self.submitted_filename = 'my_file.py'
        self.project_filename = 'testy.py'

        self.admin = obj_ut.create_dummy_user()
        self.project = obj_ut.build_project(
            course_kwargs={'administrators': [self.admin]},
            project_kwargs={
                'required_student_files': [self.submitted_filename]})

        self.project.add_project_file(
            SimpleUploadedFile(self.project_filename, b''))

        self.starter_args = {
            'name': 'steve',
            'student_resource_files': [self.submitted_filename],
            'test_resource_files': [self.project_filename],
            'project': self.project
        }


class InterpretedAutograderTestCaseTestCase(_SetUpBase, TemporaryFilesystemTestCase):
    def setUp(self):
        super().setUp()

    def test_valid_init_with_defaults(self):
        test = ag_models.AutograderTestCaseFactory.validate_and_create(
            'interpreted_test_case', interpreter='python',
            entry_point_filename=self.project_filename,
            **self.starter_args)

        loaded = ag_models.AutograderTestCaseBase.objects.get(pk=test.pk)

        self.assertEqual('python', loaded.interpreter)
        self.assertEqual([], loaded.interpreter_flags)
        self.assertEqual(self.project_filename, loaded.entry_point_filename)

        self.assertEqual('interpreted_test_case', loaded.get_type_str())

    def test_valid_init_no_defaults(self):
        flags = ['spam', 'egg']
        test = ag_models.AutograderTestCaseFactory.validate_and_create(
            'interpreted_test_case',
            interpreter='python3',
            interpreter_flags=flags,
            entry_point_filename=self.project_filename,
            **self.starter_args)

        loaded = ag_models.AutograderTestCaseBase.objects.get(pk=test.pk)

        self.assertEqual('python3', loaded.interpreter)
        self.assertEqual(flags, loaded.interpreter_flags)
        self.assertEqual(self.project_filename, loaded.entry_point_filename)

        self.assertEqual('interpreted_test_case', loaded.get_type_str())

    def test_error_unsupported_interpreter(self):
        with self.assertRaises(ValidationError) as cm:
            ag_models.AutograderTestCaseFactory.validate_and_create(
                'interpreted_test_case',
                interpreter='not_an_interpreter',
                entry_point_filename=self.project_filename,
                **self.starter_args)

        self.assertTrue('interpreter' in cm.exception.message_dict)

    def test_invalid_interpreter_flags(self):
        with self.assertRaises(ValidationError) as cm:
            ag_models.AutograderTestCaseFactory.validate_and_create(
                'interpreted_test_case',
                interpreter='python',
                interpreter_flags=['good', 'bad; #><'],
                entry_point_filename=self.project_filename,
                **self.starter_args)

        self.assertTrue('interpreter_flags'in cm.exception.message_dict)

    def test_entry_point_not_test_resource_file(self):
        with self.assertRaises(ValidationError) as cm:
            ag_models.AutograderTestCaseFactory.validate_and_create(
                'interpreted_test_case',
                interpreter='python',
                entry_point_filename='waaaaa',
                **self.starter_args)

        self.assertTrue('entry_point_filename' in cm.exception.message_dict)

# -----------------------------------------------------------------------------
# -----------------------------------------------------------------------------


class RunInterpretedAutograderTestCaseTestCase(_SetUpBase, TemporaryFilesystemTestCase):
    @classmethod
    def setUpClass(class_):
        name = 'unit-test-sandbox-{}'.format(uuid.uuid4().hex)

        class_.sandbox = AutograderSandbox(name=name)
        class_.sandbox.start()

    @classmethod
    def tearDownClass(class_):
        class_.sandbox.stop()

    def setUp(self):
        super().setUp()

        with open(self.project_filename, 'w') as f:
            f.write(PyProgs.other_module)

        self.test = ag_models.AutograderTestCaseFactory.validate_and_create(
            'interpreted_test_case',
            interpreter='python3',
            entry_point_filename=self.project_filename,
            **self.starter_args)

    def test_zero_return_code_and_stdout(self):
        with open(self.submitted_filename, 'w') as f:
            f.write(PyProgs.normal_exit)

        self.sandbox.copy_into_sandbox(
            self.project_filename, self.submitted_filename)
        result = self.test.run(None, self.sandbox)

        self.assertEqual(0, result.return_code)
        self.assertEqual('hello world\nwaluigi\n', result.standard_output)
        self.assertEqual('', result.standard_error_output)

    def test_nonzero_return_code_and_stderr(self):
        with open(self.submitted_filename, 'w') as f:
            f.write(PyProgs.bad_exit)

        self.sandbox.copy_into_sandbox(
            self.project_filename, self.submitted_filename)
        result = self.test.run(None, self.sandbox)

        self.assertEqual(0, result.return_code)
        self.assertEqual('waluigi\n', result.standard_output)
        self.assertEqual('lulz\n', result.standard_error_output)

# -----------------------------------------------------------------------------


class PyProgs:
    normal_exit = """
print('hello world')
"""

    bad_exit = """
import sys
print('lulz', file=sys.stderr)
"""

    other_module = """
import my_file

print('waluigi')
"""
