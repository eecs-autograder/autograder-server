import os
import shutil

from django.db import models
from django.core.exceptions import ValidationError

from autograder.models.model_utils import (
    ModelValidatableOnSave, ManagerWithValidateOnCreate)
import autograder.shared.global_constants as gc
import autograder.shared.utilities as ut


class Course(ModelValidatableOnSave):
    """
    Represents a programming course for which students will be submitting
    code to an autograder.

    Primary key: name

    Fields:
        name -- The name of this course.
                Must be unique, non-empty and non-null.

        semesters -- A django manager object that can be used to query
            Semesters that belong to this Course.

    Overridden member functions:
        save()
        clean()
        delete()
    """
    objects = ManagerWithValidateOnCreate()

    # -------------------------------------------------------------------------

    name = models.CharField(
        max_length=gc.MAX_CHAR_FIELD_LEN, primary_key=True)

    # -------------------------------------------------------------------------

    def save(self, *args, **kwargs):
        super().save(*args, **kwargs)

        course_root_dir = ut.get_course_root_dir(self)
        if not os.path.isdir(course_root_dir):
            # Since the database is in charge or validating the uniqueness
            # of this course, we can assume at this point that creating
            # the course directory will succeed. If for some reason it fails,
            # this will be considered a more severe error, and the OSError
            # thrown by os.makedirs will be handled at a higher level.

            # print('creating: ' + course_root_dir)
            os.makedirs(course_root_dir)

    def clean(self):
        if self.name:
            self.name = self.name.strip()

        errors = {}
        if not self.name:
            errors['name'] = "Name can't be empty"

        if errors:
            raise ValidationError(errors)

    def delete(self, *args, **kwargs):
        course_root_dir = ut.get_course_root_dir(self)
        super().delete(*args, **kwargs)

        shutil.rmtree(course_root_dir)
