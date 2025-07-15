from unittest import mock
from django.core import mail
from autograder.utils.testing import UnitTestBase
from django.conf import settings
from autograder.core.models.group.group_invitation_email import send_group_invitation_email
import autograder.utils.testing.model_obj_builders as obj_build


class _SetUp:
    def setUp(self):
        # Set up mock data for testing
        self.sender = obj_build.create_dummy_user()  # Username is the email
        self.recipients = obj_build.create_dummy_users(4)  # Usernames as emails
        self.project = obj_build.build_project(
            project_kwargs={"name": "Test Project"},
            course_kwargs={"name": "Test Course"}
        )


class SendGroupInvitationEmailTestCase(_SetUp, UnitTestBase):
    @mock.patch('autograder.core.models.group.group_invitation_email.sign_email')
    def test_send_group_invitation_email_success(self, mock_sign_email):
        # Mock the signing of the email content
        mock_sign_email.side_effect = lambda content: content + "\n(Signed Content)"

        # Call the function to send emails
        send_group_invitation_email(
            sender=self.sender,
            recipients=self.recipients,
            project=self.project,
            course_name=self.project.course.name,
        )

        # Assertions
        self.assertEqual(len(mail.outbox), 1)  # Only one email should be sent
        email = mail.outbox[0]

        # Check email subject
        self.assertTrue(email.subject.startswith("Invitation to Join Group for"))
        self.assertIn(self.project.name, email.subject)
        self.assertIn(self.project.course.name, email.subject)

        # Check email recipients
        self.assertCountEqual(email.to, [r.email for r in self.recipients])

        # Check email body content
        self.assertIn(self.sender.username, email.body)  # Sender's email (username) in body
        self.assertIn(self.project.name, email.body)
        self.assertIn(self.project.course.name, email.body)
        self.assertIn(f"{settings.SITE_DOMAIN}/web/project/{self.project.pk}", email.body)
        self.assertIn("(Signed Content)", email.body)  # Verify signing

    @mock.patch('autograder.core.models.group.group_invitation_email.sign_email')
    def test_send_group_invitation_email_signing_error(self, mock_sign_email):
        # Simulate a signing error
        mock_sign_email.side_effect = Exception("Signing Error")

        # Test that the RuntimeError is raised
        with self.assertRaises(RuntimeError) as context:
            send_group_invitation_email(
                sender=self.sender,
                recipients=self.recipients,
                project=self.project,
                course_name=self.project.course.name,
            )

        # Verify the exception message
        self.assertIn("Error sending group invitation email: Signing Error",
                      str(context.exception))

        # Verify no email was sent
        self.assertEqual(len(mail.outbox), 0)

    def test_send_group_invitation_email_no_recipients(self):
        with self.assertRaises(ValueError) as context:
            send_group_invitation_email(
                sender=self.sender,
                recipients=[],  # No recipients
                project=self.project,
                course_name=self.project.course.name,
            )

        # Assertions
        self.assertEqual(str(context.exception), "Recipients list cannot be empty.")
        self.assertEqual(len(mail.outbox), 0)  # No email should be sent

    def test_send_group_invitation_email_missing_project(self):
        # Call with a None project to simulate missing project
        with self.assertRaises(AttributeError) as context:
            send_group_invitation_email(
                sender=self.sender,
                recipients=self.recipients,
                project=None,  # Missing project
                course_name="Test Course",
            )

        # Assertions
        self.assertEqual(str(context.exception), "Project cannot be None")
        self.assertEqual(len(mail.outbox), 0)  # No email should be sent
