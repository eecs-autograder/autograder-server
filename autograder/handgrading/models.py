from django.db import models
from autograder.core.fields import EnumField
from django.core import validators
from django.core.exceptions import ValidationError
from enum import Enum

from autograder.core.models import AutograderModel, Project, Submission


class PointsStyle(Enum):
    """
    Ways hangrading points can be managed
    """
    start_at_zero_and_add = "start_at_zero_and_add",
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

    project = models.ForeignKey(Project)


class Criterion(AutograderModel):
    """
    Rubric item with fixed points that is not line specific
    """
    short_description = models.TextField(blank=True)

    long_description = models.TextField(blank=True)

    points = models.FloatField()

    handgrading_rubric = models.ForeignKey(HandgradingRubric)


class Annotation(AutograderModel):
    """
    Additional field that can be applied to a submission. Can be line specific
    """
    short_description = models.TextField(blank=True)

    long_description = models.TextField(blank=True)

    points = models.FloatField()

    handgrading_rubric = models.ForeignKey(HandgradingRubric)


class HandgradingResult(AutograderModel):
    """
    Tied to a specific submission
    """
    submission = models.OneToOneField(Submission)


class CriterionResult(AutograderModel):
    """
    Tied to a criterion object, specifies such criterion is selected
    """
    selected = models.BooleanField()

    criterion = models.ForeignKey(Criterion)

    handgrading_result = models.ForeignKey(HandgradingResult)


class AppliedAnnotation(AutograderModel):
    """
    Tied to an annotation object, specifies where the annotation is applied and if a comment
    was left with it
    """
    comment = models.TextField(blank=True)

    location = models.OneToOneField('Location', related_name='+')

    annotation = models.ForeignKey(Annotation)

    handgrading_result = models.ForeignKey(HandgradingResult)

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


class Comment(AutograderModel):
    """
    Comment left by staff or grader regarding submission. Can be applied to specific line
    """
    location = models.OneToOneField('Location', related_name='+')

    text = models.TextField()

    handgrading_result = models.ForeignKey(HandgradingResult)

    def clean(self):
        if self.location.filename not in self.handgrading_result.submission.submitted_filenames:
            raise ValidationError('Filename is not part of submitted files')

    SERIALIZABLE_FIELDS = ('pk',
                           'last_modified',
                           'location',
                           'text',
                           'handgrading_result',)

    TRANSPARENT_TO_ONE_FIELDS = ('location',)

class ArbitraryPoints(AutograderModel):
    """
    Any arbitrary points specified by staff or grader for submission
    """
    location = models.OneToOneField('Location', related_name='+')

    text = models.TextField(blank=True)

    points = models.FloatField()

    handgrading_result = models.ForeignKey(HandgradingResult)

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
