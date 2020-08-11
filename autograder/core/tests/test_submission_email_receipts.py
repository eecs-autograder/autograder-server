import base64
from unittest import mock

from django.core import mail
from django.test import Client
from django.urls import reverse

import autograder.core.models as ag_models
import autograder.utils.testing.model_obj_builders as obj_build
from autograder.core.submission_email_receipts import (check_signature,
                                                       send_submission_received_email,
                                                       send_submission_score_summary_email)
from autograder.core.submission_feedback import (SubmissionResultFeedback,
                                                 update_denormalized_ag_test_results)
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

        verification_url = email.body.strip().split('\n')[-5]
        client = Client()
        verified = client.get(verification_url).content.decode()
        self.assertIn('Signature verification SUCCESS.', verified)
        self.assertIn('BEGIN PGP SIGNATURE', verified)


class SendNonDeferredTestsFinishedEmailTestCase(UnitTestBase):
    def setUp(self):
        super().setUp()
        self.mock_submission_result_feedback = mock.Mock(wraps=SubmissionResultFeedback)

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
        with mock.patch('autograder.core.submission_email_receipts.SubmissionResultFeedback',
                        new=self.mock_submission_result_feedback):
            send_submission_score_summary_email(submission)
            self.mock_submission_result_feedback.assert_called_once_with(
                submission, ag_models.FeedbackCategory.normal, mock.ANY
            )
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

        verification_url = email.body.strip().split('\n')[-5]
        print(verification_url)
        client = Client()
        verified = client.get(verification_url).content.decode()
        self.assertIn('Signature verification SUCCESS.', verified)
        self.assertIn('BEGIN PGP SIGNATURE', verified)

    def test_email_content_for_past_limit_submission(self) -> None:
        group = obj_build.make_group(num_members=2)
        submission = obj_build.make_submission(group=group, is_past_daily_limit=True)

        submission = update_denormalized_ag_test_results(submission.pk)
        with mock.patch('autograder.core.submission_email_receipts.SubmissionResultFeedback',
                        new=self.mock_submission_result_feedback):
            send_submission_score_summary_email(submission)
            self.assertEqual(1, len(mail.outbox))
            self.mock_submission_result_feedback.assert_called_once_with(
                submission, ag_models.FeedbackCategory.past_limit_submission, mock.ANY
            )


class SignatureVerificationFailureTest(UnitTestBase):
    def test_invalid_signature(self) -> None:
        modified_msg = """-----BEGIN PGP SIGNED MESSAGE-----
Hash: SHA512

WAAAAAAAAA I modified this
-----BEGIN PGP SIGNATURE-----

iQEzBAEBCgAdFiEEmeYf8s7aXw/z5x5QxcGsohCi7WUFAl8Vq0UACgkQxcGsohCi
7WW0IAgAjV0rfZd0HIDq5uZbrmG2MlwbKHRXpMNpF98XDNoZV2MKfWvFdRDRWe1b
O5dmVcC6KlL0LgimvaI2kpTzwLw2rFVzskg0Clg+a2KAKqYkNoGfZHbQTjbjd5N5
WMI1tcwC0dXrg/rq0xW7RC6OsNurvGLRA85cHD7mP+vODLcxPvnbQ23uaUfheIVA
PapIwG+C+J+rACQWT9syo0ztniFQBJ668Sco8mGjSEUvOkJUM+L72A5FDFMKPO0r
SsOmJQioxMyfU9VuOWeRndk0ksmc9t4n16rQtZma26PVxaMwiN4s/fDTJ/OXG3NZ
RT7C5fR2QiosmGCDXGUNDQ8HMnwrpg==
=i+Z+
-----END PGP SIGNATURE-----
        """

        encoded = base64.urlsafe_b64encode(modified_msg.encode()).decode()
        verified, _ = check_signature(encoded)
        self.assertFalse(verified)

        url = reverse(
            'verify-submission-receipt-email',
            kwargs={'encoded_signed_msg': encoded}
        )
        client = Client()
        decrypted = client.get(url).content.decode()
        self.assertIn('Signature verification FAILED.', decrypted)
