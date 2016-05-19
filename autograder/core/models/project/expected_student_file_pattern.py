from django.db import models
from django.core import validators, exceptions

from ..ag_model_base import AutograderModel
from .project import Project

import autograder.core.shared.utilities as ut
import autograder.utilities.fields as ag_fields


class ExpectedStudentFilePattern(AutograderModel):
    """
    These objects describe Unix-style shell patterns that files
    submitted by students can or should match.
    """
    class Meta:
        unique_together = ('pattern', 'project')

    _DEFAULT_TO_DICT_FIELDS = frozenset([
        'project',
        'pattern',
        'min_num_matches',
        'max_num_matches',
    ])

    @classmethod
    def get_default_to_dict_fields(class_):
        return class_._DEFAULT_TO_DICT_FIELDS

    _EDITABLE_FIELDS = frozenset([
        'pattern',
        'min_num_matches',
        'max_num_matches',
    ])

    @classmethod
    def get_editable_fields(class_):
        return class_._EDITABLE_FIELDS

    project = models.ForeignKey(Project,
                                related_name='expected_student_file_patterns')

    pattern = ag_fields.ShortStringField(
        validators=[ut.check_shell_style_file_pattern],
        help_text='''A shell-style file pattern suitable for
            use with Python's fnmatch.fnmatch()
            function (https://docs.python.org/3.4/library/fnmatch.html)
            This string may contain the same characters allowed in
            project or student files as well as special pattern
            matching characters. This string must not be empty.
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
