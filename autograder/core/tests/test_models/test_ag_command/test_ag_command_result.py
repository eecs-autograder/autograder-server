import autograder.core.models as ag_models
from autograder.utils.testing import UnitTestBase


class AGCommandResultTestCase(UnitTestBase):
    def setUp(self):
        super().setUp()
        self.ag_cmd = ag_models.AGCommand.objects.validate_and_create(cmd='waaaluigi time')

    def test_default_init(self):
        result = ag_models.AGCommandResult.objects.validate_and_create()
        self.assertIsNone(result.return_code)
        self.assertFalse(result.timed_out)
        self.assertFalse(result.stdout_truncated)
        self.assertFalse(result.stderr_truncated)

    def test_cmd_result_stdout_and_stderr_files(self):
        result = ag_models.AGCommandResult.objects.validate_and_create()
        result2 = ag_models.AGCommandResult.objects.validate_and_create()

        self.assertNotEqual(result.stdout_filename, result.stderr_filename)
        self.assertNotEqual(result.stdout_filename, result2.stdout_filename)
        self.assertNotEqual(result.stderr_filename, result2.stderr_filename)

        with result.open_stdout('w') as f:
            f.write('text1')

        with result2.open_stderr('w') as f:
            f.write('text2')

        with result2.open_stdout('w') as f:
            f.write('text3')

        with result.open_stderr('w') as f:
            f.write('text4')

        with result.open_stdout('r') as f:
            self.assertEqual('text1', f.read())

        with result2.open_stderr('r') as f:
            self.assertEqual('text2', f.read())

        with result2.open_stdout('r') as f:
            self.assertEqual('text3', f.read())

        with result.open_stderr('r') as f:
            self.assertEqual('text4', f.read())
