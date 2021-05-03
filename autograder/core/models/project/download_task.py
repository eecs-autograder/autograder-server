from django.db import models

from autograder.core.models.ag_model_base import AutograderModelManager

from ..task import Task
from .project import Project


class DownloadType(models.TextChoices):
    all_scores = 'all_scores'
    final_graded_submission_scores = 'final_graded_submission_scores'
    all_submission_files = 'all_submission_files'
    final_graded_submission_files = 'final_graded_submission_files'


class DownloadTask(Task):
    objects = AutograderModelManager['DownloadTask']()

    project = models.ForeignKey(Project, related_name='download_tasks', on_delete=models.CASCADE)
    download_type = models.TextField(choices=DownloadType.choices)
    result_filename = models.TextField(blank=True)

    SERIALIZABLE_FIELDS = (
        'pk',
        'project',
        'download_type',
        'result_filename',
        'progress',
        'error_msg',
        'created_at',
    )

    EDITABLE_FIELDS = (
        'result_filename',
        'progress',
        'error_msg',
    )
