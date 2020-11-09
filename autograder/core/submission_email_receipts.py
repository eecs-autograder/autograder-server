import base64
import logging
import traceback
from decimal import Decimal
from typing import Protocol, Tuple, Union

import gnupg  # type: ignore
from django.conf import settings
from django.core.mail import send_mail
from django.urls import reverse
from django.utils.functional import cached_property

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
            sign_email(content),
            settings.EMAIL_FROM_ADDR,
            group.member_names,
            # fail_silently=True
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
            sign_email(content),
            settings.EMAIL_FROM_ADDR,
            group.member_names,
            # fail_silently=True
        )
    except Exception as e:
        logger = logging.getLogger(__name__)
        logger.error(traceback.format_exc())
        traceback.print_exc()


_PropOrCachedProp = Union[
    Union[Decimal, int], 'cached_property[Union[Decimal, int]]'
]


class HasPoints(Protocol):
    @property
    def total_points(self) -> _PropOrCachedProp:
        ...

    @property
    def total_points_possible(self) -> _PropOrCachedProp:
        ...


def _get_points_str(has_points: HasPoints) -> str:
    if has_points.total_points_possible != 0:
        return f'{has_points.total_points}/{has_points.total_points_possible}'

    return ''


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


# Decodes the given data and returns a tuple of:
# (<verification succeeded>, <original message>)
def check_signature(encoded_signed_msg: bytes) -> Tuple[bool, str]:
    gpg = gnupg.GPG(gnupghome=settings.SECRETS_DIR)
    signed = base64.urlsafe_b64decode(encoded_signed_msg)

    verified = gpg.verify(signed)
    return bool(verified), signed.decode()
