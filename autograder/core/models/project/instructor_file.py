from __future__ import annotations

import os
import shutil
from typing import IO, Any, AnyStr, BinaryIO, Dict, Literal, TextIO, Tuple, overload

from django.core import exceptions
from django.db import models, transaction
from django.db.models.fields.files import File

import autograder.core.constants as const
import autograder.core.utils as core_ut
from autograder import utils

from ..ag_model_base import AutograderModel, AutograderModelManager
from .project import Project


# Remove in v5
def _get_project_file_upload_to_path(instance: InstructorFile, filename: str) -> str:
    return os.path.join(core_ut.get_project_files_relative_dir(instance.project), filename)


# Remove in v5
def _validate_filename(file_obj: File) -> None:
    core_ut.check_filename(file_obj.name)


class InstructorFileManager(AutograderModelManager['InstructorFile']):
    def validate_and_create(self, *, file_obj: File, project: Project) -> InstructorFile:
        if file_obj.size > const.MAX_INSTRUCTOR_FILE_SIZE:
            raise exceptions.ValidationError(
                {'content': 'Instructor files cannot be bigger than {} bytes'.format(
                    const.MAX_INSTRUCTOR_FILE_SIZE)})

        filename = os.path.basename(file_obj.name)
        core_ut.check_filename(filename)

        with transaction.atomic():
            instructor_file = super().validate_and_create(name=filename, project=project)
            with open(instructor_file.abspath, 'wb') as dest:
                shutil.copyfileobj(file_obj.file, dest)

            return instructor_file


class InstructorFile(AutograderModel):
    """
    These objects provide a means for storing uploaded files
    to be used in project test cases.
    """
    class Meta:
        ordering = ('name',)
        unique_together = ('name', 'project')

    objects = InstructorFileManager()

    SERIALIZABLE_FIELDS = (
        'pk',
        'project',
        'name',
        'last_modified',
        'size',
    )

    project = models.ForeignKey(Project, related_name='instructor_files', on_delete=models.CASCADE)
    name = models.TextField()
    # Remove in v5
    _remove_in_v5_file_obj = models.FileField(
        upload_to=_get_project_file_upload_to_path,
        max_length=const.MAX_CHAR_FIELD_LEN * 2,
        blank=True, null=True)

    def rename(self, new_name: str) -> None:
        """
        Renames the file stored in this model instance.
        Any path information in new_name is stripped before renaming the
        file, for security reasons.
        """
        new_name = os.path.basename(new_name)
        try:
            core_ut.check_filename(new_name)
        except exceptions.ValidationError as e:
            raise exceptions.ValidationError({'name': e.message})

        new_filename_exists = utils.find_if(
            self.project.instructor_files.exclude(pk=self.pk),
            lambda file_: file_.name == new_name
        )

        if new_filename_exists:
            raise exceptions.ValidationError(
                {'filename': 'File {} already exists'.format(new_name)})

        old_abspath = self.abspath
        self.name = new_name
        new_abspath = self.abspath
        # NOTE: We use copy instead of move because we don't actually have
        # to delete the old file from the filesystem (move over a network
        # does a copy and then a delete).
        # This helps us guarantee the atomicity of this operation. This works
        # because creating and renaming a file can simply overwrite the
        # file in the filesystem if the name ever gets re-used.
        shutil.copy(old_abspath, new_abspath)

        self.save()

    @property
    def abspath(self) -> str:
        return os.path.join(core_ut.get_project_files_dir(self.project), self.name)

    @property
    def size(self) -> int:
        return os.path.getsize(self.abspath)

    @transaction.atomic
    def delete(self, *args: Any, **kwargs: Any) -> Tuple[int, Dict[str, int]]:
        from ..ag_test.ag_test_command import AGTestCommand, ExpectedOutputSource, StdinSource

        AGTestCommand.objects.filter(
            stdin_source=StdinSource.instructor_file,
            stdin_instructor_file=self,
        ).update(stdin_source=StdinSource.none)

        AGTestCommand.objects.filter(
            expected_stdout_source=ExpectedOutputSource.instructor_file,
            expected_stdout_instructor_file=self,
        ).update(expected_stdout_source=ExpectedOutputSource.none)

        AGTestCommand.objects.filter(
            expected_stderr_source=ExpectedOutputSource.instructor_file,
            expected_stderr_instructor_file=self,
        ).update(expected_stderr_source=ExpectedOutputSource.none)

        return_val = super().delete(*args, **kwargs)
        # NOTE: We don't actually have to delete the file from the filesystem.
        # This helps us guarantee the atomicity of this operation. This works
        # because creating and renaming a file can simply overwrite the
        # file in the filesystem if the name ever gets re-used.

        return return_val

    @overload
    def open(self, mode: Literal['r', 'w']) -> TextIO:
        ...

    @overload
    def open(self, mode: Literal['rb', 'wb']) -> BinaryIO:
        ...

    def open(self, mode: Literal['r', 'w', 'rb', 'wb'] = 'r') -> IO[AnyStr]:
        return open(self.abspath, mode)
