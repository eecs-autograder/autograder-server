import csv
import os
import traceback
import uuid
import zipfile
from typing import Sequence, Callable, Iterator, Tuple

from celery import shared_task
from django.conf import settings

import autograder.core.models as ag_models
from autograder.core.models.get_ultimate_submissions import get_ultimate_submissions
import autograder.core.utils as core_ut
from autograder import utils


@shared_task(queue='project_downloads', acks_late=True)
def all_submission_files_task(project_pk, task_pk, include_staff, *args, **kwargs):
    _make_download_file_task_impl(project_pk, task_pk, include_staff,
                                  _get_all_submissions, _make_submission_archive)


@shared_task(queue='project_downloads', acks_late=True)
def ultimate_submission_files_task(project_pk, task_pk, include_staff, *args, **kwargs):
    _make_download_file_task_impl(project_pk, task_pk, include_staff,
                                  _get_ultimate_submissions, _make_submission_archive)


@shared_task(queue='project_downloads', acks_late=True)
def all_submission_scores_task(project_pk, task_pk, include_staff, *args, **kwargs):
    def _get_all_finished_grading_submissions(project: ag_models.Project,
                                              groups: Sequence[ag_models.SubmissionGroup]):
        submissions = list(
            ag_models.get_submissions_with_results_queryset(
                ag_models.FeedbackCategory.max,
                base_manager=ag_models.Submission.objects.filter(
                    submission_group__in=groups,
                    status=ag_models.Submission.GradingStatus.finished_grading)))
        return submissions, len(submissions)

    _make_download_file_task_impl(project_pk, task_pk, include_staff,
                                  _get_all_finished_grading_submissions, _make_scores_csv)


@shared_task(queue='project_downloads', acks_late=True)
def ultimate_submission_scores_task(project_pk, task_pk, include_staff, *args, **kwargs):
    _make_download_file_task_impl(project_pk, task_pk, include_staff,
                                  _get_ultimate_submissions, _make_scores_csv)


# Given a project and a sequence of submission groups, return a tuple of
# (submissions, num_submissions).
GetSubmissionsFnType = Callable[[ag_models.Project, Sequence[ag_models.SubmissionGroup]],
                                Tuple[Iterator[ag_models.Submission], int]]


def _get_all_submissions(project: ag_models.Project,
                         groups: Sequence[ag_models.SubmissionGroup]):
    submissions = list(ag_models.Submission.objects.filter(submission_group__in=groups))
    return submissions, len(submissions)


def _get_ultimate_submissions(project: ag_models.Project,
                              groups: Sequence[ag_models.SubmissionGroup]):
    return get_ultimate_submissions(project, *(group.pk for group in groups)), len(groups)


# Given a task, an iterator of submissions, the number of submissions
# that iterator will generate, and a destination filename, create
# a downloadable file with the given destination filename, updating
# the task's progress field as the file is generated.
MakeDownloadFnType = Callable[[ag_models.DownloadTask, Iterator[ag_models.Submission], int, str],
                              None]


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


def _get_groups(project, include_staff) -> Sequence[ag_models.SubmissionGroup]:
    groups = project.submission_groups.all()
    groups = filter(lambda group: group.submissions.count(), groups)
    if not include_staff:
        groups = filter(
            lambda group: not project.course.is_course_staff(group.members.first()), groups)
    groups = list(groups)
    return groups


def _make_download_result_filename(project: ag_models.project,
                                   task: ag_models.DownloadTask) -> str:
    downloads_dir = os.path.join(settings.MEDIA_ROOT, 'project_downloads')
    os.makedirs(downloads_dir, exist_ok=True)
    filename = '{}-{}-{}'.format(project.pk, task.download_type.value, uuid.uuid4().hex)
    return os.path.join(downloads_dir, filename)


# Download task progress will be updated every _PROGRESS_UPDATE_FREQUENCY
# submissions processed.
_PROGRESS_UPDATE_FREQUENCY = 50


def _make_submission_archive(task, submissions, num_submissions, dest_filename):
    with open(dest_filename, 'wb') as archive:
        with zipfile.ZipFile(archive, 'w') as z:
            for index, s in enumerate(submissions):
                archive_dirname = '_'.join(
                    sorted(s.submission_group.member_names)) + '-' + s.timestamp.isoformat()
                with utils.ChangeDirectory(core_ut.get_submission_dir(s)):
                    for filename in s.submitted_filenames:
                        target_name = os.path.join(
                            '{}_{}'.format(task.project.course.name, task.project.name),
                            archive_dirname, filename)
                        z.write(filename, arcname=target_name)

                if index % _PROGRESS_UPDATE_FREQUENCY == 0:
                    task.progress = (index / num_submissions) * 100
                    task.save()
                    print('Updated task {} progress: {}'.format(task.pk, task.progress))


def _make_scores_csv(task, submissions, num_submissions, dest_filename):
    with open(dest_filename, 'w', newline='') as csv_file:
        writer = csv.writer(csv_file)

        project = task.project
        username_headers = ['Username {}'.format(i + 1) for i in range(project.max_group_size)]
        row_headers = username_headers + ['Timestamp', 'Total', 'Total Possible']
        for suite in project.ag_test_suites.all():
            row_headers += ['{} Total'.format(suite.name),
                            '{} Total Possible'.format(suite.name)]
            row_headers += ['{} - {}'.format(suite.name, case.name)
                            for case in suite.ag_test_cases.all()]

        writer.writerow(row_headers)

        sorted_submissions = sorted(submissions,
                                    key=lambda s: min(s.submission_group.member_names))
        for index, submission in enumerate(sorted_submissions):
            row = sorted(submission.submission_group.member_names)
            if len(row) < project.max_group_size:
                row += ['' for i in range(project.max_group_size - len(row))]
            row.append(submission.timestamp.isoformat())
            fdbk = submission.get_fdbk(ag_models.FeedbackCategory.max)
            row += [fdbk.total_points, fdbk.total_points_possible]
            for suite_result in fdbk.ag_test_suite_results:
                suite_fdbk = suite_result.get_fdbk(ag_models.FeedbackCategory.max)
                row += [suite_fdbk.total_points, suite_fdbk.total_points_possible]
                for case_result in suite_fdbk.ag_test_case_results:
                    row.append(case_result.get_fdbk(ag_models.FeedbackCategory.max).total_points)

            writer.writerow(row)

            if index % _PROGRESS_UPDATE_FREQUENCY == 0:
                task.progress = (index / num_submissions) * 100
                task.save()
                print('Updated task {} progress: {}'.format(task.pk, task.progress))
