import warnings
from typing import Iterator, Iterable

from django.db.models import Prefetch, prefetch_related_objects

from .project import Project, UltimateSubmissionPolicy
from .ag_test.feedback_category import FeedbackCategory
from .submission_group import SubmissionGroup
from .submission import Submission, get_submissions_with_results_queryset


def get_ultimate_submission(group: SubmissionGroup) -> Submission:
    result = list(get_ultimate_submissions(group.project, group))
    if not result:
        return None

    return result[0]


def get_ultimate_submissions(project: Project, *groups: SubmissionGroup) -> Iterator[Submission]:
    finished_submissions_queryset = Submission.objects.filter(
        status=Submission.GradingStatus.finished_grading)
    if not groups:
        groups = project.submission_groups.all()

    if project.ultimate_submission_policy == UltimateSubmissionPolicy.most_recent:
        prefetch_related_objects(groups, Prefetch('submissions', finished_submissions_queryset))
        return (group.submissions.first() for group in groups if group.submissions.count())
    elif project.ultimate_submission_policy == UltimateSubmissionPolicy.best_with_normal_fdbk:
        warnings.warn('best_with_normal_fdbk is currently untested and may be deprecated soon.',
                      PendingDeprecationWarning)

        submissions_queryset = get_submissions_with_results_queryset(
            FeedbackCategory.normal, base_manager=finished_submissions_queryset)
        prefetch_related_objects(groups, Prefetch('submissions', submissions_queryset))
        return _best_submissions_generator(groups, FeedbackCategory.normal)
    elif project.ultimate_submission_policy == UltimateSubmissionPolicy.best:
        submissions_queryset = get_submissions_with_results_queryset(
            FeedbackCategory.max, base_manager=finished_submissions_queryset)
        prefetch_related_objects(groups, Prefetch('submissions', submissions_queryset))
        return _best_submissions_generator(groups, FeedbackCategory.max)


def _best_submissions_generator(groups: Iterable[SubmissionGroup],
                                fdbk_category: FeedbackCategory):
    for group in groups:
        submissions = list(group.submissions.all())
        if len(submissions) == 0:
            continue

        yield max(submissions,
                  key=lambda submission: submission.get_fdbk(fdbk_category).total_points)
