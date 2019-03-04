from django.core import validators, exceptions
from django.db import models

import autograder.core.fields as ag_fields
import autograder.core.utils as core_ut
from .project import Project
from ..ag_model_base import AutograderModel


class ExpectedStudentFile(AutograderModel):
    """
    These objects describe Unix-style shell patterns that files
    submitted by students can or should match.
    """
    class Meta:
        unique_together = ('pattern', 'project')

    SERIALIZABLE_FIELDS = (
        'pk',
        'project',
        'pattern',
        'min_num_matches',
        'max_num_matches',
        'last_modified',
    )

    EDITABLE_FIELDS = (
        'pattern',
        'min_num_matches',
        'max_num_matches',
    )

    project = models.ForeignKey(Project, on_delete=models.CASCADE,
                                related_name='expected_student_files')

    pattern = ag_fields.ShortStringField(
        validators=[core_ut.check_filename],
        help_text='''A shell-style file pattern suitable for
            use with Python's fnmatch.fnmatch()
            function (https://docs.python.org/3.5/library/fnmatch.html)
            This string must be a legal UNIX filename and may not be
            '..' or '.'.
            NOTE: Patterns for a given project must not overlap,
                otherwise the behavior is undefined.''')

    min_num_matches = models.IntegerField(
        default=1,
        validators=[validators.MinValueValidator(0)],
        help_text='''The minimum number of submitted student files that
            should match the pattern. Must be non-negative.''')

    max_num_matches = models.IntegerField(
        default=1,
        help_text='''The maximum number of submitted student files that
            can match the pattern. Must be >= min_num_matches''')

    def clean(self):
        if self.max_num_matches < self.min_num_matches:
            raise exceptions.ValidationError(
                {'max_num_matches': (
                    'Maximum number of matches must be greater than or '
                    'equal to minimum number of matches')})
