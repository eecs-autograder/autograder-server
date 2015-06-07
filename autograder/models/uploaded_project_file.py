import os

from django.db import models
from django.core.exceptions import SuspiciousFileOperation

from autograder.models import Project
from autograder.shared import utilities as ut


class UploadedProjectFile:
    """
    """
    @staticmethod
    def _get_upload_path(instance, filename):
        file_basename = os.path.basename(filename)
        if filename != file_basename:
            raise SuspiciousFileOperation(
                "Attempt was made to manipulate the upload directory "
                "of a file: " + filename)

        return os.path.join(
            ut.get_project_files_dir(instance.project), file_basename)

    project = models.ForeignKey(Project)
    uploaded_file = models.FileField(
        max_length=None, upload_to=_get_upload_path)
