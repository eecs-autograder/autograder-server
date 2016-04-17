from django.db import models

from ..ag_model_base import AutograderModel
from .project import Project

import autograder.core.shared.utilities as ut
import autograder.utilities.fields as ag_fields


class RequiredStudentFile(AutograderModel):
    """
    These objects describe files that students are required to submit.
    """
    class Meta:
        unique_together = ('project', 'filename')

    project = models.ForeignKey(Project, related_name='required_student_files')

    filename = ag_fields.ShortStringField(
        validators=[ut.check_user_provided_filename],
        help_text='''See check_user_provided_filename comments
            for restrictions on the character set used for filenames.
            ''')
