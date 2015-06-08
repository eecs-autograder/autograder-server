import os

from django.db import models
from django.core.exceptions import (
    SuspiciousFileOperation, ObjectDoesNotExist,
    MultipleObjectsReturned, ValidationError)

from autograder.models import Project
from autograder.models.model_utils import ModelValidatedOnSave
from autograder.shared import utilities as ut


def _get_upload_path(filename, project):
    """
    Computes the path to which a project file should be uploaded.

    Raises SuspiciousFileOperation if filename contains more than just
    the basename of a file. For example, "spam.txt" is a legal filename,
    but "eggs/spam.txt" and "../spam.txt" are not.
    """
    file_basename = os.path.basename(filename)
    if filename != file_basename:
        raise SuspiciousFileOperation(
            "Attempt was made to manipulate the upload directory "
            "of a file: " + filename)

    result = os.path.join(
        ut.get_project_files_dir(project), file_basename)
    # print("upload path: " + result)
    return result


class UploadedProjectFile(ModelValidatedOnSave):
    """
    Represents an uploaded file that is used for a particular project.

    Fields:
        project -- The project this file belongs to.
        uploaded_file -- This field provides access to the actual file
                         in the file system.

    Overridden methods:
        validate_fields()
        save()

    Static methods:
        get_project_file()
    """
    project = models.ForeignKey(Project)
    uploaded_file = models.FileField(
        max_length=500,
        upload_to=(lambda instance, filename:
                   _get_upload_path(filename, instance.project)))
    # overwrite_on_save = models.BooleanField(default=False)

    # -------------------------------------------------------------------------
    # -------------------------------------------------------------------------

    @staticmethod
    def get_project_file(filename, project):
        """
        Given a project and a file basename (such as spam.txt), tries to
        load the corresponding UploadedProjectFile.

        Raises django's ObjectDoesNotExist if the file couldn't be found.
        Raises django's MultipleObjectsReturned if more than one potential
        match was found.
        """
        query_set = UploadedProjectFile.objects.filter(
            project=project,
            uploaded_file=_get_upload_path(filename, project))

        if not len(query_set):
            raise ObjectDoesNotExist("File not found: " + filename)

        if len(query_set) > 1:
            raise MultipleObjectsReturned(
                "More than one match found for {0} file: {1}".format(
                    project.name, filename))

        return query_set[0]

    # -------------------------------------------------------------------------

    def validate_fields(self):
        save_path = _get_upload_path(self.uploaded_file.name, self.project)
        # if not self.overwrite_on_save and os.path.exists(save_path):
        if os.path.exists(save_path):
            raise ValidationError(
                "File {0} already exists for project {1}".format(
                    self.uploaded_file.name, self.project.name))
