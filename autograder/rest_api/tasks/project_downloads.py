import csv
import os
import traceback
import uuid
import zipfile
from typing import Sequence, Callable, Iterator, Tuple, List

from celery import shared_task
from django.conf import settings

import autograder.core.models as ag_models
from autograder.core.models.get_ultimate_submissions import get_ultimate_submissions
import autograder.core.utils as core_ut
from autograder import utils
from autograder.core.submission_feedback import (
    SubmissionResultFeedback, AGTestPreLoader, MutationTestSuitePreLoader)
from autograder.rest_api.views.submission_views.all_ultimate_submission_results_view import (
    serialize_ultimate_submission_results)


@shared_task(queue='project_downloads', acks_late=True)
def all_submission_files_task(project_pk, task_pk, include_staff, *args, **kwargs):
    _make_download_file_task_impl(project_pk, task_pk, include_staff,
                                  _get_all_submissions, _make_submission_archive)


def _get_all_submissions(
        project: ag_models.Project,
        groups: Sequence[ag_models.Group]) -> Tuple[List[SubmissionResultFeedback], int]:
    ag_test_loader = AGTestPreLoader(project)
    mutation_test_suite_loader = MutationTestSuitePreLoader(project)
    submissions = [
        SubmissionResultFeedback(
            submission,
            ag_models.FeedbackCategory.max,
            ag_test_loader,
            mutation_test_suite_loader
        )
        for submission in ag_models.Submission.objects.filter(group__in=groups)
    ]
    return submissions, len(submissions)


@shared_task(queue='project_downloads', acks_late=True)
def ultimate_submission_files_task(project_pk, task_pk, include_staff, *args, **kwargs):
    _make_download_file_task_impl(project_pk, task_pk, include_staff,
                                  _get_ultimate_submissions, _make_submission_archive)


@shared_task(queue='project_downloads', acks_late=True)
def all_submission_scores_task(project_pk, task_pk, include_staff, *args, **kwargs):
    def _get_all_finished_grading_submissions(
            project: ag_models.Project, groups: Sequence[ag_models.Group]
    ) -> Tuple[List[SubmissionResultFeedback], int]:
        submissions = ag_models.get_submissions_with_results_queryset(
            base_manager=ag_models.Submission.objects.filter(
                group__in=groups,
                status=ag_models.Submission.GradingStatus.finished_grading
            )
        )
        ag_test_loader = AGTestPreLoader(project)
        mutation_test_suite_loader = MutationTestSuitePreLoader(project)
        fdbks = [
            SubmissionResultFeedback(
                submission,
                ag_models.FeedbackCategory.max,
                ag_test_loader,
                mutation_test_suite_loader
            )
            for submission in submissions
        ]
        return fdbks, len(submissions)

    _make_download_file_task_impl(project_pk, task_pk, include_staff,
                                  _get_all_finished_grading_submissions, _make_scores_csv)


@shared_task(queue='project_downloads', acks_late=True)
def ultimate_submission_scores_task(project_pk, task_pk, include_staff, *args, **kwargs):
    _make_download_file_task_impl(project_pk, task_pk, include_staff,
                                  _get_ultimate_submissions, _make_ultimate_submission_scores_csv)


# Given a project and a sequence of submission groups, return a tuple of
# (submissions, num_submissions).
GetSubmissionsFnType = Callable[[ag_models.Project, Sequence[ag_models.Group]],
                                Tuple[Iterator[SubmissionResultFeedback], int]]


def _get_ultimate_submissions(
        project: ag_models.Project,
        groups: Sequence[ag_models.Group]) -> Tuple[Iterator[SubmissionResultFeedback], int]:
    submissions = get_ultimate_submissions(
        project, filter_groups=groups, ag_test_preloader=AGTestPreLoader(project))
    return submissions, len(groups)


# Given a task, an iterator of SubmissionResultFeedbacks,
# the number of submissions that iterator will generate,
# and a destination filename, create
# a downloadable file with the given destination filename, updating
# the task's progress field as the file is generated.
MakeDownloadFnType = Callable[
    [ag_models.DownloadTask, Iterator[SubmissionResultFeedback], int, str], None]


def _make_download_file_task_impl(project_pk, task_pk, include_staff,
                                  get_submissions_fn: GetSubmissionsFnType,
                                  make_download_fn: MakeDownloadFnType):
    task = ag_models.DownloadTask.objects.get(pk=task_pk)
    try:
        project = ag_models.Project.objects.get(pk=project_pk)
        groups = _get_groups(project, include_staff)
        submissions, num_submissions = get_submissions_fn(project, groups)
        result_filename = _make_download_result_filename(project, task)
        make_download_fn(task, submissions, num_submissions, result_filename)
        task.result_filename = result_filename
        task.progress = 100
        task.save()
    except Exception:
        traceback.print_exc()
        task.error_msg = traceback.format_exc()
        task.save()


def _get_groups(project, include_staff) -> Sequence[ag_models.Group]:
    groups = project.groups.all()
    groups = filter(lambda group: group.submissions.count(), groups)
    if not include_staff:
        groups = filter(
            lambda group: not project.course.is_staff(group.members.first()), groups)
    groups = list(groups)

    return groups


def _make_download_result_filename(project: ag_models.project,
                                   task: ag_models.DownloadTask) -> str:
    downloads_dir = os.path.join(settings.MEDIA_ROOT, 'project_downloads')
    os.makedirs(downloads_dir, exist_ok=True)
    filename = '{}-{}-{}'.format(project.pk, task.download_type, uuid.uuid4().hex)
    return os.path.join(downloads_dir, filename)


# Download task progress will be updated every _PROGRESS_UPDATE_FREQUENCY
# submissions processed.
_PROGRESS_UPDATE_FREQUENCY = 50


def _make_submission_archive(task: ag_models.DownloadTask,
                             submission_fdbks: Iterator[SubmissionResultFeedback],
                             num_submissions, dest_filename):
    with open(dest_filename, 'wb') as archive:
        with zipfile.ZipFile(archive, 'w') as z:
            for index, fdbk in enumerate(submission_fdbks):
                submission = fdbk.submission
                archive_dirname = ('_'.join(submission.group.member_names)
                                   + '-' + submission.timestamp.isoformat())
                with utils.ChangeDirectory(core_ut.get_submission_dir(submission)):
                    for filename in submission.submitted_filenames:
                        target_name = os.path.join(
                            '{}_{}'.format(task.project.course.name, task.project.name),
                            archive_dirname, filename)
                        z.write(filename, arcname=target_name)

                if index % _PROGRESS_UPDATE_FREQUENCY == 0:
                    task.progress = (index / num_submissions) * 100
                    task.save()
                    print('Updated task {} progress: {}'.format(task.pk, task.progress))


def _make_scores_csv(task: ag_models.DownloadTask,
                     submission_fdbks: Iterator[SubmissionResultFeedback],
                     num_submissions: int, dest_filename: str):
    with open(dest_filename, 'w', newline='') as csv_file:
        project = task.project  # type: ag_models.Project

        user_tmpl = 'Username {}'
        timestamp_header = 'Timestamp'
        total_header = 'Total'
        total_possible_header = 'Total Possible'

        username_headers = [user_tmpl.format(i + 1) for i in range(project.max_group_size)]
        row_headers = username_headers + [timestamp_header, total_header, total_possible_header]

        row_headers += _make_test_detail_headers(project)

        writer = csv.DictWriter(csv_file, row_headers)
        writer.writeheader()

        for progress_index, fdbk in enumerate(submission_fdbks):
            submission = fdbk.submission
            row = {timestamp_header: submission.timestamp.isoformat()}

            for index, username in enumerate(submission.group.member_names):
                row[user_tmpl.format(index + 1)] = username

            row[total_header] = fdbk.total_points
            row[total_possible_header] = fdbk.total_points_possible

            row.update(_make_test_detail_columns(fdbk.to_dict()))

            writer.writerow(row)

            if progress_index % _PROGRESS_UPDATE_FREQUENCY == 0:
                task.progress = (progress_index / num_submissions) * 100
                task.save()
                print('Updated task {} progress: {}'.format(task.pk, task.progress))


def _make_ultimate_submission_scores_csv(task: ag_models.DownloadTask,
                                         submission_fdbks: Iterator[SubmissionResultFeedback],
                                         num_submissions: int, dest_filename: str):
    project_has_handgrading = False
    if hasattr(task.project, 'handgrading_rubric'):
        project_has_handgrading = True

    results = serialize_ultimate_submission_results(submission_fdbks, full_results=True,
                                                    include_handgrading=project_has_handgrading)

    with open(dest_filename, 'w', newline='') as csv_file:
        headers = [
            'Username', 'Group Members', 'Timestamp', 'Extension',
            'Total Points', 'Total Points Possible'
        ]

        if project_has_handgrading:
            headers += ['Handgrading Total Points', 'Handgrading Total Points Possible']

        headers += _make_test_detail_headers(task.project)

        writer = csv.DictWriter(csv_file, headers)
        writer.writeheader()

        for progress_index, result in enumerate(results):
            if result['ultimate_submission'] is None:
                continue

            row = {
                'Username': result['username'],
                'Group Members': ','.join(result['group']['member_names']),
                'Timestamp': result['ultimate_submission']['timestamp'],
                'Extension': result['group']['extended_due_date'],
                'Total Points': result['ultimate_submission']['results']['total_points'],
                'Total Points Possible': (
                    result['ultimate_submission']['results']['total_points_possible']),
            }

            if project_has_handgrading:
                row['Handgrading Total Points'] = (
                    result['ultimate_submission']['results']['handgrading_total_points'])
                row['Handgrading Total Points Possible'] = (
                    result['ultimate_submission']['results']['handgrading_total_points_possible'])

            row.update(_make_test_detail_columns(result['ultimate_submission']['results']))

            writer.writerow(row)

            if progress_index % _PROGRESS_UPDATE_FREQUENCY == 0:
                task.progress = (progress_index / num_submissions) * 100
                task.save()
                print('Updated task {} progress: {}'.format(task.pk, task.progress))


AG_SUITE_TOTAL_TMPL = '{} Total'
AG_SUITE_TOTAL_POSSIBLE_TMPL = '{} Total Possible'
AG_TEST_HEADER_TMPL = '{} - {}'
MUTATION_SUITE_TOTAL_TMPL = '{} Total'
MUTATION_SUITE_TOTAL_POSSIBLE_TMPL = '{} Total Possible'


def _make_test_detail_headers(project: ag_models.Project):
    headers = []
    AG_SUITE_TOTAL_TMPL = '{} Total'
    AG_SUITE_TOTAL_POSSIBLE_TMPL = '{} Total Possible'
    AG_TEST_HEADER_TMPL = '{} - {}'
    MUTATION_SUITE_TOTAL_TMPL = '{} Total'
    MUTATION_SUITE_TOTAL_POSSIBLE_TMPL = '{} Total Possible'

    for suite in project.ag_test_suites.all():
        headers += [AG_SUITE_TOTAL_TMPL.format(suite.name),
                    AG_SUITE_TOTAL_POSSIBLE_TMPL.format(suite.name)]
        headers += [AG_TEST_HEADER_TMPL.format(suite.name, case.name)
                    for case in suite.ag_test_cases.all()]

    for suite in project.mutation_test_suites.all():
        headers += [MUTATION_SUITE_TOTAL_TMPL.format(suite.name),
                    MUTATION_SUITE_TOTAL_POSSIBLE_TMPL.format(suite.name)]

    return headers


def _make_test_detail_columns(submission_fdbk_dict: dict):
    row = {}
    for suite_fdbk in submission_fdbk_dict['ag_test_suite_results']:
        ag_suite_total_header = AG_SUITE_TOTAL_TMPL.format(suite_fdbk['ag_test_suite_name'])
        row[ag_suite_total_header] = suite_fdbk['total_points']
        ag_suite_total_possible_header = AG_SUITE_TOTAL_POSSIBLE_TMPL.format(
            suite_fdbk['ag_test_suite_name'])
        row[ag_suite_total_possible_header] = suite_fdbk['total_points_possible']

        for case_fdbk in suite_fdbk['ag_test_case_results']:
            ag_test_total_header = AG_TEST_HEADER_TMPL.format(
                suite_fdbk['ag_test_suite_name'], case_fdbk['ag_test_case_name'])
            row[ag_test_total_header] = case_fdbk['total_points']

    for suite_fdbk in submission_fdbk_dict['mutation_test_suite_results']:
        mutation_suite_total_header = MUTATION_SUITE_TOTAL_TMPL.format(
            suite_fdbk['mutation_test_suite_name'])
        row[mutation_suite_total_header] = suite_fdbk['total_points']

        mutation_suite_total_possible_header = MUTATION_SUITE_TOTAL_POSSIBLE_TMPL.format(
            suite_fdbk['mutation_test_suite_name'])
        row[mutation_suite_total_possible_header] = suite_fdbk['total_points_possible']

    return row
