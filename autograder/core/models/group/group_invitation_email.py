import base64
import gnupg  # type: ignore
from typing import Any, Collection, Dict, List, cast

from django.contrib.auth.models import User
from django.conf import settings
from django.core.mail import send_mail
from django.urls import reverse
from ..project import Project


# Makes the following modifications to content and returns the result:
# 1. Signs content with GPG
# 2. Generates a URL that, when visited, will verify the GPG signature.
#    That URL is appended to content.
def sign_email(content: str) -> str:
    gpg = gnupg.GPG(gnupghome=settings.SECRETS_DIR)
    signed = str(
        gpg.sign(content,
                 keyid=settings.GPG_KEY_ID,
                 passphrase=settings.GPG_KEY_PASSWORD))

    url_encoded_signed = base64.urlsafe_b64encode(signed.encode()).decode()
    url = (
        settings.SITE_DOMAIN
        + reverse('verify-submission-receipt-email',
                  kwargs={'encoded_signed_msg': url_encoded_signed})
    )
    signed += f"""\nTo see if this message is authentic, visit the link below.
The contents of that page should match the above message body and receipt ID.
{url}

Alternatively, you can verify this message using GPG.
Visit https://eecs-autograder.github.io/autograder.io/topics/verifying_email_receipts.html
for instructions.
"""
    return signed


def send_group_invitation_email(
        sender: User,
        recipients: Collection[User],
        project: Project,
        course_name: str,
) -> None:
    """
    Sends a cryptographically-verifiable
    email to invite recipients
    to join a group for a project.
    """
    if project is None:
        raise AttributeError("Project cannot be None")
    if not recipients:
        raise ValueError("Recipients list cannot be empty.")

    try:
        # Construct the email content
        content = f"""You have been invited by {sender.username} to join a group for the
        "{project.name}" in the course "{course_name}".

        To respond to this invitation, please visit the following link:
        {settings.SITE_DOMAIN}/web/project/{project.pk}

        If you have any questions, please contact {sender}.
        """
        # Prepare the list of recipient email addresses
        recipient_emails = [recipient.email for recipient in recipients]

        # Send the email using Django's send_mail
        send_mail(
            f'Invitation to Join Group for {course_name} - {project.name}',
            sign_email(content),  # Sign the email content for security
            settings.EMAIL_FROM_ADDR,
            recipient_emails,
            # fail_silently=True to avoid crashes if an email fails
        )
    except Exception as e:
        # Directly raise the error instead of logging
        raise RuntimeError(f"Error sending group invitation email: {str(e)}") from e
