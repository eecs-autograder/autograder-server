import os
import shutil

from django.db import models, transaction
from django.conf import settings
from django.core import exceptions

import autograder.core.utils as core_ut
import autograder.core.constants as const
from autograder import utils

from ..ag_model_base import AutograderModel, AutograderModelManager
from .project import Project


def _get_project_file_upload_to_path(instance, filename):
    return os.path.join(
        core_ut.get_project_files_relative_dir(instance.project), filename)


# For migrations backwards compatibility
def _get_project_file_upload_to_dir(instance, filename):
    return _get_project_file_upload_to_path(instance, filename)


def _validate_filename(file_obj):
    core_ut.check_user_provided_filename(file_obj.name)


class UploadedFileManager(AutograderModelManager):
    def validate_and_create(self, **kwargs):
        if 'file_obj' in kwargs and 'project' in kwargs:
            file_obj = kwargs['file_obj']
            project = kwargs['project']

            file_exists = utils.find_if(
                project.uploaded_files.all(),
                lambda uploaded: uploaded.name == file_obj.name)
            if file_exists:
                raise exceptions.ValidationError(
                    {'filename': 'File {} already exists'.format(file_obj.name)})

        return super().validate_and_create(**kwargs)


class UploadedFile(AutograderModel):
    """
    These objects provide a means for storing uploaded files
    to be used in project test cases.
    """
    objects = UploadedFileManager()

    SERIALIZABLE_FIELDS = (
        'project',
        'name',
        'size',
    )

    project = models.ForeignKey(Project, related_name='uploaded_files')
    file_obj = models.FileField(
        upload_to=_get_project_file_upload_to_path,
        validators=[_validate_filename],
        max_length=const.MAX_CHAR_FIELD_LEN * 2)

    @property
    def name(self):
        return self.basename

    def rename(self, new_name):
        """
        Renames the file stored in this model instance.
        Any path information in new_name is stripped before renaming the
        file, for security reasons.
        """
        new_name = os.path.basename(new_name)
        try:
            core_ut.check_user_provided_filename(new_name)
        except exceptions.ValidationError as e:
            raise exceptions.ValidationError({'name': e.message})

        old_abspath = self.abspath
        self.file_obj.name = _get_project_file_upload_to_path(self, new_name)
        new_abspath = self.abspath

        shutil.move(old_abspath, new_abspath)
        self.save()

    @property
    def abspath(self):
        return os.path.join(settings.MEDIA_ROOT, self.file_obj.name)

    @property
    def basename(self):
        return os.path.basename(self.file_obj.name)

    @property
    def size(self):
        return self.file_obj.size

    def delete(self, **kwargs):
        with transaction.atomic():
            file_path = self.abspath
            return_val = super().delete()
            os.remove(file_path)

            return return_val

    def open(self, mode='r'):
        return open(self.abspath)
