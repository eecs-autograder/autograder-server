import os

import autograder.core.models as ag_models
from autograder.utils.testing import UnitTestBase
import autograder.core.utils as core_ut


class AGCommandResultTestCase(UnitTestBase):
    def test_default_init(self):
        result = ag_models.AGCommandResult.objects.validate_and_create()
        result.refresh_from_db()

        self.assertIsNone(result.return_code)
        self.assertFalse(result.timed_out)
        self.assertFalse(result.stdout_truncated)
        self.assertFalse(result.stderr_truncated)

        expected_stdout_path = os.path.join(core_ut.misc_cmd_output_dir(),
                                            'cmd_result_{}_stdout'.format(result.pk))
        expected_stderr_path = os.path.join(core_ut.misc_cmd_output_dir(),
                                            'cmd_result_{}_stderr'.format(result.pk))
        self.assertEqual(expected_stdout_path, result.stdout_filename)
        self.assertEqual(expected_stderr_path, result.stderr_filename)

        stdout = 'spaaaaam'
        stderr = 'egggggggg'

        with open(result.stdout_filename, 'w') as f:
            f.write(stdout)

        with open(result.stderr_filename, 'w') as f:
            f.write(stderr)

        with open(result.stdout_filename) as f:
            self.assertEqual(stdout, f.read())

        with open(result.stderr_filename) as f:
            self.assertEqual(stderr, f.read())

    def test_error_cmd_result_not_saved_stdout_and_stderr_filename(self):
        unsaved_result = ag_models.AGCommandResult()
        with self.assertRaises(AttributeError):
            print(unsaved_result.stdout_filename)

        with self.assertRaises(AttributeError):
            print(unsaved_result.stderr_filename)
