from django.core import exceptions, validators
from django.db import models

import autograder.core.utils as core_ut
from autograder.core.constants import MAX_CHAR_FIELD_LEN

from ..ag_model_base import AutograderModel, AutograderModelManager
from .project import Project


class ExpectedStudentFile(AutograderModel):
    """
    These objects describe Unix-style shell patterns that files
    submitted by students can or should match.
    """
    objects = AutograderModelManager['ExpectedStudentFile']()

    class Meta:
        ordering = ('pattern',)
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

    pattern = models.CharField(
        max_length=MAX_CHAR_FIELD_LEN,
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

    def clean(self) -> None:
        if self.max_num_matches < self.min_num_matches:
            raise exceptions.ValidationError(
                {'max_num_matches': (
                    'Maximum number of matches must be greater than or '
                    'equal to minimum number of matches')})
