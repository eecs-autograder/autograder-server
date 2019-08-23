import autograder.core.models as ag_models
import autograder.utils.testing.model_obj_builders as obj_build
from autograder.core.submission_feedback import update_denormalized_ag_test_results
from autograder.utils.testing import UnitTestBase


class AGTestSuiteResultTestCase(UnitTestBase):
    def setUp(self):
        super().setUp()

        self.submission = obj_build.make_submission()
        self.project = self.submission.group.project

        self.ag_suite = obj_build.make_ag_test_suite(self.project)

        # Make sure that ag tests and ag test results don't have
        # overlapping pks.
        for i in range(20):
            self.ag_suite.delete()
            self.ag_suite.pk = None
            self.ag_suite.save()

    def test_create_suite_defaults(self):
        suite_result = ag_models.AGTestSuiteResult.objects.validate_and_create(
            ag_test_suite=self.ag_suite, submission=self.submission
        )

        self.assertEqual(self.ag_suite, suite_result.ag_test_suite)

        self.assertIsNone(suite_result.setup_return_code)
        self.assertFalse(suite_result.setup_timed_out)
        self.assertFalse(suite_result.setup_stdout_truncated)
        self.assertFalse(suite_result.setup_stderr_truncated)

    def test_create_suite_no_defaults(self):
        suite_res_kwargs = {
            'ag_test_suite': self.ag_suite,
            'submission': self.submission,
            'setup_return_code': 1,
            'setup_timed_out': False,
            'setup_stdout_truncated': True,
            'setup_stderr_truncated': False
        }

        suite_res = ag_models.AGTestSuiteResult.objects.validate_and_create(**suite_res_kwargs)

        for field_name, value in suite_res_kwargs.items():
            self.assertEqual(value, getattr(suite_res, field_name))

    def test_serialization_for_denormalzation(self):
        expected_keys = [
            'pk',

            'ag_test_suite_id',
            'submission_id',
            'setup_return_code',
            'setup_timed_out',
            'setup_stdout_truncated',
            'setup_stderr_truncated',

            'ag_test_case_results'
        ]

        suite_result = ag_models.AGTestSuiteResult.objects.validate_and_create(
            ag_test_suite=self.ag_suite, submission=self.submission
        )

        self.assertCountEqual(expected_keys, suite_result.to_dict().keys())

    def test_delete_suite_result_denormed_results_updated(self):
        suite_result = ag_models.AGTestSuiteResult.objects.validate_and_create(
            ag_test_suite=self.ag_suite, submission=self.submission
        )
        self.assertNotEqual(suite_result.pk, self.ag_suite.pk)

        dont_delete_suite = obj_build.make_ag_test_suite(self.project)
        dont_delete_suite_result = ag_models.AGTestSuiteResult.objects.validate_and_create(
            ag_test_suite=dont_delete_suite, submission=self.submission
        )
        self.assertNotEqual(dont_delete_suite.pk, dont_delete_suite_result.pk)

        submission2 = obj_build.make_submission(group=obj_build.make_group(project=self.project))
        suite_result2 = ag_models.AGTestSuiteResult.objects.validate_and_create(
            ag_test_suite=self.ag_suite, submission=submission2
        )
        self.assertNotEqual(suite_result2.pk, self.ag_suite.pk)

        self.submission = update_denormalized_ag_test_results(self.submission.pk)
        self.assertIn(str(dont_delete_suite.pk), self.submission.denormalized_ag_test_results)

        submission2 = update_denormalized_ag_test_results(submission2.pk)

        for submission, suite_res in ((self.submission, suite_result),
                                      (submission2, suite_result2)):
            submission.refresh_from_db()
            self.assertIn(str(suite_res.ag_test_suite_id), submission.denormalized_ag_test_results)

        self.ag_suite.delete()

        for submission, suite_res in ((self.submission, suite_result),
                                      (submission2, suite_result2)):
            submission.refresh_from_db()
            self.assertNotIn(str(suite_res.ag_test_suite_id),
                             submission.denormalized_ag_test_results)

        self.submission.refresh_from_db()
        self.assertIn(str(dont_delete_suite.pk), self.submission.denormalized_ag_test_results)
