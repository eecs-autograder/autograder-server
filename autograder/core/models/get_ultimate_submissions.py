import warnings
from typing import Iterator, Optional, List, Sequence

from django.contrib.auth.models import User
from django.db.models import Prefetch

from autograder.core.submission_feedback import (
    SubmissionResultFeedback, AGTestPreLoader, MutationTestSuitePreLoader)
from .project import Project, UltimateSubmissionPolicy
from .ag_test.feedback_category import FeedbackCategory
from .group import Group
from .submission import Submission, get_submissions_with_results_queryset


def get_ultimate_submission(group: Group, user: Optional[User]=None) -> Optional[Submission]:
    project = group.project
    [group] = _prefetch_submissions(project, [group])
    if project.ultimate_submission_policy == UltimateSubmissionPolicy.most_recent:
        return _get_most_recent_submission(group, user)
    elif project.ultimate_submission_policy == UltimateSubmissionPolicy.best_with_normal_fdbk:
        best = _get_best_submission(
            group,
            FeedbackCategory.normal,
            ag_test_preloader=AGTestPreLoader(project),
            mutation_test_suite_preloader=MutationTestSuitePreLoader(project),
            user=user
        )
        return best.submission if best is not None else None
    elif project.ultimate_submission_policy == UltimateSubmissionPolicy.best:
        best = _get_best_submission(
            group,
            FeedbackCategory.max,
            ag_test_preloader=AGTestPreLoader(project),
            mutation_test_suite_preloader=MutationTestSuitePreLoader(project),
            user=user
        )
        return best.submission if best is not None else None


def get_ultimate_submissions(
    project: Project,
    *, filter_groups: Optional[Sequence[Group]], ag_test_preloader: AGTestPreLoader
) -> Iterator[SubmissionResultFeedback]:
    """
    :param project: The Project to load final graded submissions from.
    :param filter_groups: If not None, load only ultimate submissions
        for the specified groups. Otherwise, load ultimate submissions
        for all groups belonging to project.
    :param ag_test_preloader: An instance of AGTestPreloader that can be
        used to efficiently fetch test case data for project.
    :return: An iterator of feedback results for ultimate submissions
        belonging to project.
    """
    filter_groups = _prefetch_submissions(project, filter_groups)

    mutation_test_suite_preloader = MutationTestSuitePreLoader(project)

    if project.ultimate_submission_policy == UltimateSubmissionPolicy.most_recent:
        return (
            SubmissionResultFeedback(
                group.submissions.first(),
                FeedbackCategory.max,
                ag_test_preloader,
                mutation_test_suite_preloader
            )
            for group in filter_groups if group.submissions.count()
        )
    elif project.ultimate_submission_policy == UltimateSubmissionPolicy.best_with_normal_fdbk:
        warnings.warn('best_with_normal_fdbk is currently untested and may be deprecated soon.',
                      PendingDeprecationWarning)

        # We need to generate best submissions with normal feedback
        # but return SubmissionResultFeedbacks with max feedback.
        best_submissions_fdbks = (
            _get_best_submission(
                group, FeedbackCategory.normal, ag_test_preloader, mutation_test_suite_preloader)
            for group in filter_groups
        )
        best_submissions = (fdbk.submission for fdbk in best_submissions_fdbks
                            if fdbk is not None)
        return (
            SubmissionResultFeedback(
                submission, FeedbackCategory.max, ag_test_preloader, mutation_test_suite_preloader)
            for submission in best_submissions)
    elif project.ultimate_submission_policy == UltimateSubmissionPolicy.best:
        best_submissions_fdbks = (
            _get_best_submission(
                group, FeedbackCategory.max, ag_test_preloader, mutation_test_suite_preloader)
            for group in filter_groups
        )
        return (fdbk for fdbk in best_submissions_fdbks if fdbk is not None)

    assert False


def _prefetch_submissions(project: Project, groups: Optional[Sequence[Group]]) -> List[Group]:
    finished_submissions_queryset = Submission.objects.filter(
        status=Submission.GradingStatus.finished_grading)

    base_group_queryset = project.groups
    if groups is not None:
        base_group_queryset = base_group_queryset.filter(pk__in=[group.pk for group in groups])

    submissions_queryset = get_submissions_with_results_queryset(
        base_manager=finished_submissions_queryset)
    return base_group_queryset.prefetch_related(Prefetch('submissions', submissions_queryset))


def _get_most_recent_submission(group: Group, user: Optional[User]=None) -> Optional[Submission]:
    for submission in group.submissions.all():
        if user is None or user.username not in submission.does_not_count_for:
            return submission

    return None


def _get_best_submission(group: Group, fdbk_category: FeedbackCategory,
                         ag_test_preloader: AGTestPreLoader,
                         mutation_test_suite_preloader: MutationTestSuitePreLoader,
                         user: Optional[User]=None) -> Optional[SubmissionResultFeedback]:
    best: Optional[SubmissionResultFeedback] = None
    for submission in group.submissions.all():
        if user is not None and user.username in submission.does_not_count_for:
            continue

        fdbk = SubmissionResultFeedback(
            submission, fdbk_category, ag_test_preloader, mutation_test_suite_preloader)
        if best is None or fdbk.total_points > best.total_points:
            best = fdbk

    return best
