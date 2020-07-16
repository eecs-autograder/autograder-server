from django.core import mail
from django.test import Client

import autograder.core.models as ag_models
import autograder.utils.testing.model_obj_builders as obj_build
from autograder.core.submission_email_receipts import (send_submission_received_email,
                                                       send_submission_score_summary_email)
from autograder.core.submission_feedback import update_denormalized_ag_test_results
from autograder.utils.testing.unit_test_base import UnitTestBase


class SendSubmissionReceivedEmailTestCase(UnitTestBase):
    def test_email_content(self) -> None:
        group = obj_build.make_group(num_members=2)
        submission = obj_build.make_submission(group=group)

        send_submission_received_email(group, submission)
        self.assertEqual(1, len(mail.outbox))

        email = mail.outbox[0]
        self.assertTrue(email.subject.startswith('Submission Received'))
        self.assertIn(group.project.course.name, email.subject)
        self.assertIn(group.project.name, email.subject)

        self.assertEqual(group.member_names, email.to)

        self.assertIn(submission.submitter, email.body)
        self.assertIn(group.project.course.name, email.body)
        self.assertIn(group.project.name, email.body)
        self.assertIn(str(submission.timestamp), email.body)

        verification_url = email.body.strip().split('\n')[-2]
        client = Client()
        decrypted = client.get(verification_url).content.decode()
        self.assertEqual(email.body.strip().split('\n')[:-4], decrypted.strip().split('\n'))


class SendNonDeferredTestsFinishedEmailTestCase(UnitTestBase):
    def test_email_content(self) -> None:
        group = obj_build.make_group(num_members=2)
        submission = obj_build.make_submission(group=group)
        project = group.project

        ag_test_suite1 = obj_build.make_ag_test_suite(project)
        ag_test_case1 = obj_build.make_ag_test_case(ag_test_suite1)
        ag_test_cmd1 = obj_build.make_full_ag_test_command(ag_test_case1)
        obj_build.make_correct_ag_test_command_result(ag_test_cmd1, submission=submission)

        ag_test_suite2 = obj_build.make_ag_test_suite(project)
        ag_test_case2 = obj_build.make_ag_test_case(ag_test_suite2)
        ag_test_cmd2 = obj_build.make_full_ag_test_command(
            ag_test_case2, set_arbitrary_points=False, set_arbitrary_expected_vals=False
        )
        cmd2_result = obj_build.make_correct_ag_test_command_result(
            ag_test_cmd2, submission=submission)

        ag_test_case3 = obj_build.make_ag_test_case(ag_test_suite2)
        ag_test_cmd3 = obj_build.make_full_ag_test_command(ag_test_case3)
        ag_test_cmd4 = obj_build.make_full_ag_test_command(ag_test_case3)
        cmd3_result = obj_build.make_incorrect_ag_test_command_result(
            ag_test_cmd3,
            ag_test_case_result=ag_models.AGTestCaseResult.objects.validate_and_create(
                ag_test_case=ag_test_case3,
                ag_test_suite_result=cmd2_result.ag_test_case_result.ag_test_suite_result
            ))
        obj_build.make_correct_ag_test_command_result(
            ag_test_cmd4, ag_test_case_result=cmd3_result.ag_test_case_result)

        deferred_test_suite = obj_build.make_ag_test_suite(project, deferred=True)

        mutation_suite1 = obj_build.make_mutation_test_suite(
            project,
            buggy_impl_names=['bug1', 'bug2', 'bug7'],
            points_per_exposed_bug=3
        )
        mutation_suite2 = obj_build.make_mutation_test_suite(project)

        mutation_suite_result1 = (
            ag_models.MutationTestSuiteResult.objects.validate_and_create(
                mutation_test_suite=mutation_suite1,
                submission=submission,
                student_tests=['test1', ['test2']],
                bugs_exposed=['bug2']
            )
        )
        mutation_suite_result2 = (
            ag_models.MutationTestSuiteResult.objects.validate_and_create(
                mutation_test_suite=mutation_suite2,
                submission=submission,
                student_tests=['tessst'],
                bugs_exposed=[]
            )
        )
        submission = update_denormalized_ag_test_results(submission.pk)
        send_submission_score_summary_email(submission)
        self.assertEqual(1, len(mail.outbox))

        email = mail.outbox[0]
        self.assertTrue(email.subject.startswith('Submission Summary'))
        self.assertIn(group.project.course.name, email.subject)
        self.assertIn(group.project.name, email.subject)

        self.assertEqual(group.member_names, email.to)

        self.assertIn(submission.submitter, email.body)
        self.assertIn(group.project.course.name, email.body)
        self.assertIn(group.project.name, email.body)
        self.assertIn(str(submission.timestamp), email.body)

        self.assertIn(ag_test_suite1.name, email.body)
        self.assertIn(ag_test_case1.name, email.body)
        # Single-command tests don't show list of commands
        self.assertNotIn(ag_test_cmd1.name, email.body)
        self.assertIn(ag_test_suite2.name, email.body)
        self.assertIn(ag_test_case2.name, email.body)
        # Single-command tests don't show list of commands
        self.assertNotIn(ag_test_cmd2.name, email.body)
        self.assertIn(ag_test_case3.name, email.body)
        self.assertIn(ag_test_cmd3.name, email.body)
        self.assertIn(ag_test_cmd4.name, email.body)
        self.assertIn(mutation_suite1.name, email.body)
        self.assertIn(mutation_suite2.name, email.body)

        self.assertNotIn(deferred_test_suite.name, email.body)

        verification_url = email.body.strip().split('\n')[-2]
        client = Client()
        decrypted = client.get(verification_url).content.decode()
        self.assertEqual(email.body.strip().split('\n')[:-4], decrypted.strip().split('\n'))
