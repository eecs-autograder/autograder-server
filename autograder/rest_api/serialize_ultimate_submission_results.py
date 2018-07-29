from typing import Iterable, List

from django.utils import timezone

import autograder.core.models as ag_models
from autograder.core.models.get_ultimate_submissions import get_ultimate_submission
from autograder.core.submission_feedback import SubmissionResultFeedback


def serialize_ultimate_submission_results(ultimate_submissions: Iterable[SubmissionResultFeedback],
                                          *, full_results: bool,
                                          include_handgrading: bool = False) -> List[dict]:
    """
    Returns serialized ultimate submission data for each user in the
    groups linked to ultimate_submissions.
    This function also accounts for submissions that don't count for
    a partecular user due to late day usage.

    :param ultimate_submissions:
    :param full_results: Whether to include information about individual
        test cases.
    :param include_handgrading:
    :return: [
        {
            "username": <username>,
            "group": <group>,
            "ultimate_submission": {
                "results": {
                    "total_points": <int>,
                    "total_points_possible": <int>,

                    // Only present if full_points is True
                    "ag_test_suite_results": [<ag test suite result details>],
                    "student_test_suite_results": [<student test suite result details>],

                    // Only present if include_handgrading is True
                    "handgrading_total_points": <int>,
                    "handgrading_total_points_possible": <int>
                },
                <submission data>
            }
        },
        ...
    ]
    """
    results = []
    for submission_fdbk in ultimate_submissions:
        submission = submission_fdbk.submission
        group = submission.group
        if group.extended_due_date is not None and group.extended_due_date > timezone.now():
            submission_data = None
        else:
            submission_data = _get_submission_data_with_results(submission_fdbk, full_results,
                                                                include_handgrading)

        group_data = group.to_dict()

        for username in group.member_names:
            user_data = {
                'username': username,
                'group': group_data,
            }

            if username in submission.does_not_count_for:
                user_ultimate_submission = get_ultimate_submission(
                    group, group.members.get(username=username))
                # NOTE: Do NOT overwrite submission_data
                user_submission_data = _get_submission_data_with_results(
                    SubmissionResultFeedback(
                        user_ultimate_submission, ag_models.FeedbackCategory.max,
                        submission_fdbk.ag_test_preloader),
                    full_results,
                    include_handgrading
                )
                user_data['ultimate_submission'] = user_submission_data
            else:
                user_data['ultimate_submission'] = submission_data

            results.append(user_data)

    return results


def _get_submission_data_with_results(submission_fdbk: SubmissionResultFeedback,
                                      full_results: bool,
                                      include_handgrading: bool = False):
    submission_data = submission_fdbk.submission.to_dict()

    if not full_results:
        submission_results = {
            'total_points': str(submission_fdbk.total_points),
            'total_points_possible': str(submission_fdbk.total_points_possible)
        }
    else:
        submission_results = submission_fdbk.to_dict()

    if include_handgrading:
        handgrading_result_available = (
            hasattr(submission_fdbk.submission, 'handgrading_result') and (
                submission_fdbk.submission.handgrading_result.finished_grading)
        )

        if handgrading_result_available:
            handgrading_result = submission_fdbk.submission.handgrading_result
            submission_results['handgrading_total_points'] = handgrading_result.total_points
            submission_results['handgrading_total_points_possible'] = (
                handgrading_result.total_points_possible)
        else:
            submission_results['handgrading_total_points'] = ''
            submission_results['handgrading_total_points_possible'] = ''

    submission_data['results'] = submission_results

    return submission_data
