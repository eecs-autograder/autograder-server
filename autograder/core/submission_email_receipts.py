import base64
import logging
import traceback
import uuid

from cryptography.fernet import Fernet
from django.conf import settings
from django.core.mail import send_mail
from django.urls import reverse

import autograder.core.models as ag_models
from autograder.core.submission_feedback import AGTestPreLoader, SubmissionResultFeedback


def send_submission_received_email(
    group: ag_models.Group, submission: ag_models.Submission
) -> None:
    """
    Sends a cryptographically-verifiable email that confirms basic
    information about the given submission.
    """
    # We don't want sending an email to unexpectedly interfere with
    # the response, so we catch exceptions and log them.
    try:
        content = f"""We've received a submission from {submission.submitter}
at {submission.timestamp} UTC for {group.project.course.name} {group.project.name}.
The submission's database ID is {submission.pk}.

Please visit {settings.SITE_DOMAIN}/web/project/{group.project.pk}?current_tab=my_submissions
to view your results as they become available.
"""
        send_mail(
            f'Submission Received: {group.project.course.name} {group.project.name}',
            add_validation_url(content),
            settings.EMAIL_FROM_ADDR,
            group.member_names,
            fail_silently=True
        )
    except Exception as e:
        logger = logging.getLogger(__name__)
        logger.error(traceback.format_exc())


def send_submission_score_summary_email(
    submission: ag_models.Submission
) -> None:
    """
    Sends a cryptographically-verifiable email with a summary of test
    case results for all non-deferred tests for the given submission.
    """
    try:
        group = submission.group

        content = f"""This email contains a summary of your score for
all non-deferred test cases on the submission from {submission.submitter}
at {submission.timestamp} UTC for {group.project.course.name} {group.project.name}.
The submission's database ID is {submission.pk}.

Please visit {settings.SITE_DOMAIN}/web/project/{group.project.pk}?current_tab=my_submissions
to view all available details on these results.\n
"""
        fdbk_category = (
            ag_models.FeedbackCategory.past_limit_submission if submission.is_past_daily_limit
            else ag_models.FeedbackCategory.normal
        )
        ag_test_preloader = AGTestPreLoader(group.project)
        fdbk = SubmissionResultFeedback(submission, fdbk_category, ag_test_preloader)

        for result in fdbk.mutation_test_suite_results:
            content += f'{result.mutation_test_suite_name}: {_get_points_str(result)}\n'

        content += '\n'

        for suite_result in fdbk.ag_test_suite_results:
            if suite_result.ag_test_suite.deferred:
                continue

            content += f'{suite_result.ag_test_suite_name}:\n'
            for test_result in suite_result.ag_test_case_results:
                content += f'\t{test_result.ag_test_case_name}: {_get_points_str(test_result)}\n'
                if len(test_result.ag_test_command_results) > 1:
                    for cmd_result in test_result.ag_test_command_results:
                        content += (
                            f'\t\t{cmd_result.ag_test_command_name}: '
                            f'{_get_points_str(cmd_result)}\n'
                        )

            content += '\n'

        content += f'\n\nTotal: {_get_points_str(fdbk)}\n'

        send_mail(
            f'Submission Summary: {group.project.course.name} {group.project.name}',
            add_validation_url(content),
            settings.EMAIL_FROM_ADDR,
            group.member_names,
            fail_silently=True
        )
    except Exception as e:
        logger = logging.getLogger(__name__)
        logger.error(traceback.format_exc())
        traceback.print_exc()


def _get_points_str(has_points):
    if has_points.total_points_possible != 0:
        return f'{has_points.total_points}/{has_points.total_points_possible}'

    return ''


# Makes the following modifications to content and returns the result:
# 1. Appends a UUID to content.
# 2. Generates a URL that, when visited, will return the decrypted
#    email receipt. That URL is appended to content.
def add_validation_url(content: str) -> str:
    content += f'\nReceipt ID: {uuid.uuid4().hex}\n'

    fernet = Fernet(settings.SUBMISSION_EMAIL_VERIFICATION_KEY)
    encrypted = base64.urlsafe_b64encode(
        fernet.encrypt(content.encode(errors='surrogateescape'))
    ).decode()
    url = (
        settings.SITE_DOMAIN
        + reverse('validate-submission-receipt-email', kwargs={'encrypted_msg': encrypted})
    )
    content += f"""\nTo validate this email receipt, please visit:
{url}
The contents of that page should match the above message body and receipt ID.
"""

    return content


def decrypt_message(encrypted_msg: bytes) -> str:
    fernet = Fernet(settings.SUBMISSION_EMAIL_VERIFICATION_KEY)
    return fernet.decrypt(
        base64.urlsafe_b64decode(encrypted_msg)
    )
