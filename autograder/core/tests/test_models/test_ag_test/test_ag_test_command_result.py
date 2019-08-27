import autograder.core.models as ag_models
import autograder.utils.testing.model_obj_builders as obj_build
from autograder.core.submission_feedback import update_denormalized_ag_test_results
from autograder.utils.testing import UnitTestBase


class AGTestCommandResultTestCase(UnitTestBase):
    def setUp(self):
        super().setUp()

        self.submission = obj_build.make_submission()
        self.project = self.submission.group.project

        self.ag_suite = obj_build.make_ag_test_suite(self.project)
        self.case = obj_build.make_ag_test_case(self.ag_suite)
        self.cmd = obj_build.make_full_ag_test_command(
            self.case,
            set_arbitrary_points=False,
            set_arbitrary_expected_vals=False
        )
        # Make sure that ag tests and ag test results don't have
        # overlapping pks.
        for i in range(20):
            self.cmd.delete()
            self.cmd.pk = None
            self.cmd.save()

        self.suite_result = ag_models.AGTestSuiteResult.objects.validate_and_create(
            ag_test_suite=self.ag_suite, submission=self.submission
        )

        self.case_result = ag_models.AGTestCaseResult.objects.validate_and_create(
            ag_test_case=self.case, ag_test_suite_result=self.suite_result
        )

    def test_create_cmd_result_defaults(self):
        cmd_res = ag_models.AGTestCommandResult.objects.validate_and_create(
            ag_test_command=self.cmd, ag_test_case_result=self.case_result
        )

        self.assertEqual(self.cmd, cmd_res.ag_test_command)
        self.assertEqual(self.case_result, cmd_res.ag_test_case_result)

        self.assertIsNone(cmd_res.return_code)
        self.assertIsNone(cmd_res.return_code_correct)
        self.assertFalse(cmd_res.timed_out)
        self.assertIsNone(cmd_res.stdout_correct)
        self.assertIsNone(cmd_res.stderr_correct)
        self.assertFalse(cmd_res.stdout_truncated)
        self.assertFalse(cmd_res.stderr_truncated)

    def test_create_cmd_result_no_defaults(self):
        cmd_res_kwargs = {
            'ag_test_command': self.cmd,
            'ag_test_case_result': self.case_result,
            'return_code': 2,
            'return_code_correct': False,
            'timed_out': True,
            'stdout_correct': False,
            'stderr_correct': True,
            'stdout_truncated': False,
            'stderr_truncated': True
        }

        cmd_res = ag_models.AGTestCommandResult.objects.validate_and_create(**cmd_res_kwargs)

        for field_name, value in cmd_res_kwargs.items():
            self.assertEqual(value, getattr(cmd_res, field_name))

    def test_serialization_for_denormalzation(self):
        expected_keys = [
            'pk',

            'ag_test_command_id',
            'ag_test_case_result_id',

            'return_code',
            'return_code_correct',

            'timed_out',

            'stdout_correct',
            'stderr_correct',

            'stdout_truncated',
            'stderr_truncated',
        ]

        cmd_res = ag_models.AGTestCommandResult.objects.validate_and_create(
            ag_test_command=self.cmd, ag_test_case_result=self.case_result
        )

        self.assertCountEqual(expected_keys, cmd_res.to_dict().keys())

    def test_delete_cmd_denormed_results_updated(self):
        cmd_res1 = ag_models.AGTestCommandResult.objects.validate_and_create(
            ag_test_command=self.cmd, ag_test_case_result=self.case_result
        )
        self.assertNotEqual(cmd_res1.pk, self.cmd.pk)

        dont_delete_cmd = obj_build.make_full_ag_test_command(self.case)
        dont_delete_cmd_result = obj_build.make_incorrect_ag_test_command_result(
            ag_test_command=dont_delete_cmd, ag_test_case_result=self.case_result,
            submission=self.submission)
        self.assertNotEqual(dont_delete_cmd.pk, dont_delete_cmd_result.pk)

        submission2 = obj_build.make_submission(group=obj_build.make_group(project=self.project))
        suite_result2 = ag_models.AGTestSuiteResult.objects.validate_and_create(
            ag_test_suite=self.ag_suite, submission=submission2
        )

        case_result2 = ag_models.AGTestCaseResult.objects.validate_and_create(
            ag_test_case=self.case, ag_test_suite_result=suite_result2
        )
        cmd_res2 = ag_models.AGTestCommandResult.objects.validate_and_create(
            ag_test_command=self.cmd, ag_test_case_result=case_result2
        )
        self.assertNotEqual(self.cmd.pk, cmd_res2.pk)

        self.submission = update_denormalized_ag_test_results(self.submission.pk)
        self.assertIn(
            str(dont_delete_cmd.pk),
            self.submission.denormalized_ag_test_results[
                str(dont_delete_cmd.ag_test_case.ag_test_suite_id)
            ]['ag_test_case_results'][
                str(dont_delete_cmd.ag_test_case_id)]['ag_test_command_results']
        )

        submission2 = update_denormalized_ag_test_results(submission2.pk)

        for submission, cmd_res in ((self.submission, cmd_res1), (submission2, cmd_res2)):
            self.assertIn(
                str(cmd_res.ag_test_command_id),
                submission.denormalized_ag_test_results[
                    str(self.ag_suite.pk)
                ]['ag_test_case_results'][str(self.case.pk)]['ag_test_command_results'])

        self.cmd.delete()

        for submission, cmd_res in ((self.submission, cmd_res1), (submission2, cmd_res2)):
            submission.refresh_from_db()

            self.assertNotIn(
                str(cmd_res.ag_test_command_id),
                submission.denormalized_ag_test_results[
                    str(self.ag_suite.pk)
                ]['ag_test_case_results'][str(self.case.pk)]['ag_test_command_results'])

        self.submission.refresh_from_db()
        self.assertIn(
            str(dont_delete_cmd.pk),
            self.submission.denormalized_ag_test_results[
                str(dont_delete_cmd.ag_test_case.ag_test_suite_id)
            ]['ag_test_case_results'][
                str(dont_delete_cmd.ag_test_case_id)]['ag_test_command_results']
        )
