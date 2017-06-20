import warnings
from typing import Sequence

from .project import Project, UltimateSubmissionPolicy
from .ag_test.feedback_category import FeedbackCategory
from .submission import Submission


def get_ultimate_submissions(project: Project, *group_pks) -> Sequence[Submission]:
    groups = project.submission_groups.prefetch_related('submissions').all()
    if group_pks:
        groups = groups.filter(pk__in=group_pks)

    if project.ultimate_submission_policy == UltimateSubmissionPolicy.most_recent:
        return (group.submissions.first() for group in groups)
    elif project.ultimate_submission_policy == UltimateSubmissionPolicy.best_with_normal_fdbk:
        warnings.warn('best_with_normal_fdbk is currently untested and may be deprecated soon.',
                      PendingDeprecationWarning)
        groups = groups.prefetch_related(
            'submissions__ag_test_suite_results__ag_test_case_results__ag_test_command_results')
        return (
            max(group.submissions.all(),
                key=lambda submission: submission.get_fdbk(FeedbackCategory.normal).total_points)
            for group in groups.all())
    elif project.ultimate_submission_policy == UltimateSubmissionPolicy.best:
        groups = groups.prefetch_related(
            'submissions__ag_test_suite_results__ag_test_case_results__ag_test_command_results')
        return (max(group.submissions.all(),
                    key=lambda submission: submission.get_fdbk(FeedbackCategory.max).total_points)
                for group in groups.all())
