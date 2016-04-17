import os

from django.db import models

from ..ag_model_base import AutograderModel
from .project import Project

import autograder.core.shared.global_constants as gc
import autograder.core.shared.utilities as ut


def _get_project_file_upload_to_dir(instance, filename):
    return os.path.join(
        ut.get_project_files_relative_dir(instance.project), filename)


def _validate_filename(file_obj):
    ut.check_user_provided_filename(file_obj.name)


class UploadedFile(AutograderModel):
    """
    These objects provide a means for storing uploaded files
    to be used in project test cases.
    """
    project = models.ForeignKey(Project, related_name='uploaded_files')
    file_obj = models.FileField(
        upload_to=_get_project_file_upload_to_dir,
        validators=[_validate_filename],
        max_length=gc.MAX_CHAR_FIELD_LEN * 2)

    @property
    def basename(self):
        return os.path.basename(self.file_obj.name)
