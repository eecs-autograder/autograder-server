from django.db import models
from autograder.core.fields import EnumField
from django.core import validators
from django.core.exceptions import ValidationError
from enum import Enum

from autograder.core.models import AutograderModel, Project, Submission, SubmissionGroup


class PointsStyle(Enum):
    """
    Ways hangrading points can be managed
    """
    start_at_zero_and_add = "start_at_zero_and_add"
    start_at_max_and_subtract = "start_at_max_and_subtract"


class HandgradingRubric(AutograderModel):
    """
    The rubric which is linked to the project and adds or subtracts points from or to the total.
    """
    points_style = EnumField(PointsStyle)

    max_points = models.IntegerField(validators=[validators.MinValueValidator(0)])

    show_grades_and_rubric_to_students = models.BooleanField()

    handgraders_can_leave_comments = models.BooleanField()

    handgraders_can_apply_arbitrary_points = models.BooleanField()

    project = models.OneToOneField(Project, related_name='handgrading_rubric')

    SERIALIZABLE_FIELDS = ('pk',
                           'last_modified',

                           'points_style',
                           'max_points',
                           'show_grades_and_rubric_to_students',
                           'handgraders_can_leave_comments',
                           'handgraders_can_apply_arbitrary_points',

                           'project',
                           'criteria',
                           'annotations',)

    EDITABLE_FIELDS = ('points_style',
                       'max_points',
                       'show_grades_and_rubric_to_students',
                       'handgraders_can_leave_comments',
                       'handgraders_can_apply_arbitrary_points',)

    SERIALIZE_RELATED = ('criteria',
                         'annotations',)


class Criterion(AutograderModel):
    """
    Rubric item with fixed points that is not line specific
    """
    short_description = models.TextField(blank=True)

    long_description = models.TextField(blank=True)

    points = models.FloatField()

    handgrading_rubric = models.ForeignKey(HandgradingRubric, related_name='criteria')

    SERIALIZABLE_FIELDS = ('pk',
                           'last_modified',

                           'short_description',
                           'long_description',
                           'points',
                           'handgrading_rubric',)

    EDITABLE_FIELDS = ('short_description',
                       'long_description',
                       'points',)


class Annotation(AutograderModel):
    """
    Additional field that can be applied to a submission. Can be line specific
    """
    short_description = models.TextField(blank=True)

    long_description = models.TextField(blank=True)

    points = models.FloatField()

    handgrading_rubric = models.ForeignKey(HandgradingRubric, related_name='annotations')

    SERIALIZABLE_FIELDS = ('pk',
                           'last_modified',

                           'short_description',
                           'long_description',
                           'points',
                           'handgrading_rubric',)

    EDITABLE_FIELDS = ('short_description',
                       'long_description',
                       'points',)


class HandgradingResult(AutograderModel):
    """
    Tied to a specific submission
    """
    submission = models.OneToOneField(Submission, related_name='handgrading_result')

    handgrading_rubric = models.ForeignKey(HandgradingRubric, related_name='handgrading_results')

    submission_group = models.OneToOneField(SubmissionGroup, related_name='handgrading_result')

    finished_grading = models.BooleanField(default=False, blank=True)

    SERIALIZABLE_FIELDS = ('pk',
                           'last_modified',

                           'submission',
                           'handgrading_rubric',
                           'submission_group',

                           'applied_annotations',
                           'arbitrary_points',
                           'comments',
                           'criterion_results',

                           'finished_grading',)

    SERIALIZE_RELATED = ('applied_annotations',
                         'arbitrary_points',
                         'comments',
                         'criterion_results',

                         'handgrading_rubric',)

    EDITABLE_FIELDS = ('finished_grading',)


class CriterionResult(AutograderModel):
    """
    Tied to a criterion object, specifies such criterion is selected
    """
    selected = models.BooleanField()

    criterion = models.ForeignKey(Criterion, related_name='criterion_results')

    handgrading_result = models.ForeignKey(HandgradingResult, related_name='criterion_results')

    SERIALIZABLE_FIELDS = ('pk',
                           'last_modified',

                           'selected',
                           'criterion',
                           'handgrading_result',)

    EDITABLE_FIELDS = ('selected',)

    SERIALIZE_RELATED = ('criterion',)


class AppliedAnnotation(AutograderModel):
    """
    Tied to an annotation object, specifies where the annotation is applied and if a comment
    was left with it
    """
    comment = models.TextField(blank=True)

    location = models.OneToOneField('Location', related_name='+')

    annotation = models.ForeignKey(Annotation)

    handgrading_result = models.ForeignKey(HandgradingResult, related_name='applied_annotations')

    def clean(self):
        if self.location.filename not in self.handgrading_result.submission.submitted_filenames:
            raise ValidationError('Filename is not part of submitted files')

    SERIALIZABLE_FIELDS = ('pk',
                           'last_modified',

                           'comment',
                           'location',
                           'annotation',
                           'handgrading_result',)

    TRANSPARENT_TO_ONE_FIELDS = ('location',)

    EDITABLE_FIELDS = ('comment',)

    SERIALIZE_RELATED = ('annotation',)


class Comment(AutograderModel):
    """
    Comment left by staff or grader regarding submission. Can be applied to specific line
    """
    # TODO: LOCATION CAN BE NULL
    location = models.OneToOneField('Location', related_name='+', null=True, blank=True)

    text = models.TextField()

    handgrading_result = models.ForeignKey(HandgradingResult, related_name='comments')

    def clean(self):
        submitted_filenames = self.handgrading_result.submission.submitted_filenames

        if self.location and self.location.filename not in submitted_filenames:
            raise ValidationError('Filename is not part of submitted files')

    SERIALIZABLE_FIELDS = ('pk',
                           'last_modified',

                           'location',
                           'text',
                           'handgrading_result',)

    TRANSPARENT_TO_ONE_FIELDS = ('location',)

    EDITABLE_FIELDS = ('text',)


class ArbitraryPoints(AutograderModel):
    """
    Any arbitrary points specified by staff or grader for submission
    """
    location = models.OneToOneField('Location', related_name='+')

    text = models.TextField(blank=True)

    points = models.FloatField()

    handgrading_result = models.ForeignKey(HandgradingResult, related_name='arbitrary_points')

    def clean(self):
        if self.location.filename not in self.handgrading_result.submission.submitted_filenames:
            raise ValidationError('Filename is not part of submitted files')

    SERIALIZABLE_FIELDS = ('pk',
                           'last_modified',

                           'location',
                           'text',
                           'points',
                           'handgrading_result',)

    TRANSPARENT_TO_ONE_FIELDS = ('location',)

    EDITABLE_FIELDS = ('text',
                       'points',)


class Location(AutograderModel):
    """
    Defined as a block of code with a starting and ending line
    """
    first_line = models.IntegerField(validators=[validators.MinValueValidator(0)])

    last_line = models.IntegerField(validators=[validators.MinValueValidator(0)])

    filename = models.TextField()

    def clean(self):
        if self.last_line is not None and (self.last_line < self.first_line):
            raise ValidationError('first line should be before last line')

    SERIALIZABLE_FIELDS = ('pk',
                           'last_modified',

                           'first_line',
                           'last_line',
                           'filename',)

    EDITABLE_FIELDS = ('first_line',
                       'last_line',)
