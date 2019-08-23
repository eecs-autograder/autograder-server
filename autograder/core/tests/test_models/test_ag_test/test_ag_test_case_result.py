import autograder.core.models as ag_models
from autograder.core.submission_feedback import update_denormalized_ag_test_results

from autograder.utils.testing import UnitTestBase
import autograder.utils.testing.model_obj_builders as obj_build


class AGTestCaseResultTestCase(UnitTestBase):
    def setUp(self):
        super().setUp()

        self.submission = obj_build.make_submission()
        self.project = self.submission.group.project

        self.ag_suite = obj_build.make_ag_test_suite(self.project)
        self.ag_suite = ag_models.AGTestSuite.objects.validate_and_create(
            name='kajsdhf', project=self.project)
        self.case = obj_build.make_ag_test_case(self.ag_suite)
        # Make sure that ag tests and ag test results don't have
        # overlapping pks.
        for i in range(20):
            self.case.delete()
            self.case.pk = None
            self.case.save()

        self.suite_result = ag_models.AGTestSuiteResult.objects.validate_and_create(
            ag_test_suite=self.ag_suite, submission=self.submission
        )

    def test_serialization_for_denormalzation(self):
        expected_keys = [
            'pk',
            'ag_test_case_id',
            'ag_test_suite_result_id',
            'ag_test_command_results'
        ]

        case_result = ag_models.AGTestCaseResult.objects.validate_and_create(
            ag_test_case=self.case, ag_test_suite_result=self.suite_result
        )

        self.assertCountEqual(expected_keys, case_result.to_dict().keys())

    def test_delete_case_result_denormed_results_updated(self):
        case_result1 = ag_models.AGTestCaseResult.objects.validate_and_create(
            ag_test_case=self.case, ag_test_suite_result=self.suite_result
        )
        self.assertNotEqual(self.case.pk, case_result1.pk)

        dont_delete_case = obj_build.make_ag_test_case(self.ag_suite)
        dont_delete_case_result = ag_models.AGTestCaseResult.objects.validate_and_create(
            ag_test_case=dont_delete_case, ag_test_suite_result=self.suite_result
        )
        self.assertNotEqual(dont_delete_case.pk, dont_delete_case_result.pk)

        submission2 = obj_build.make_submission(group=obj_build.make_group(project=self.project))
        suite_result2 = ag_models.AGTestSuiteResult.objects.validate_and_create(
            ag_test_suite=self.ag_suite, submission=submission2
        )

        case_result2 = ag_models.AGTestCaseResult.objects.validate_and_create(
            ag_test_case=self.case, ag_test_suite_result=suite_result2
        )
        self.assertNotEqual(self.case.pk, case_result2.pk)

        self.submission = update_denormalized_ag_test_results(self.submission.pk)
        self.assertIn(
            str(dont_delete_case.pk),
            self.submission.denormalized_ag_test_results[
                str(dont_delete_case.ag_test_suite_id)
            ]['ag_test_case_results']
        )

        submission2 = update_denormalized_ag_test_results(submission2.pk)

        for submission, case_res in ((self.submission, case_result1), (submission2, case_result2)):
            submission.refresh_from_db()

            self.assertIn(
                str(case_res.ag_test_case_id),
                self.submission.denormalized_ag_test_results[
                    str(self.ag_suite.pk)
                ]['ag_test_case_results']
            )

        self.case.delete()

        for submission, case_res in ((self.submission, case_result1), (submission2, case_result2)):
            submission.refresh_from_db()

            self.assertNotIn(
                str(case_res.ag_test_case_id),
                self.submission.denormalized_ag_test_results[
                    str(self.ag_suite.pk)
                ]['ag_test_case_results']
            )

        self.submission.refresh_from_db()
        self.assertIn(
            str(dont_delete_case.pk),
            self.submission.denormalized_ag_test_results[
                str(dont_delete_case.ag_test_suite_id)
            ]['ag_test_case_results']
        )
