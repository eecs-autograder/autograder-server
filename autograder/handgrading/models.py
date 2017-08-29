from django.db import models
from autograder.core.fields import EnumField
import autograder.core.models as ag_models
from django.core import validators
from django.core.exceptions import ValidationError
from enum import Enum


class PointsStyle(Enum):
    start_at_zero_and_add = "start_at_zero_and_add",
    start_at_max_and_subtract = "start_at_max_and_subtract"


class HandgradingRubric(ag_models.AutogarderModel):
    """
    The rubric which is linked to the project and adds or subtracts points from or to the total.
    """
    points_style = EnumField(PointsStyle)

    max_points = models.IntegerField(validators=[validators.MinValueValidator(0)])

    show_grades_and_rubric_to_students = models.BooleanField()

    handgraders_can_leave_comments = models.BooleanField()

    handgraders_can_apply_arbitrary_points = models.BooleanField()

    project = models.ForeignKey(ag_models.Project)


class Criterion(ag_models.AutograderModel):
    short_description = models.TextField()

    long_description = models.TextField()

    points = models.FloatField()

    handgrading_rubric = models.ForeignKey(HandgradingRubric)


class Annotation(ag_models.AutograderModel):
    short_description = models.TextField()

    long_description = models.TextField()

    points = models.FloatField()

    handgrading_rubric = models.ForeignKey(HandgradingRubric)


class HandgradingResult(ag_models.AutograderModel):
    submission = models.OneToOneField(ag_models.Submission)


class CriterionResult(ag_models.AutograderModel):
    selected = models.BooleanField()

    criterion = models.ForeignKey(Criterion)

    handgrading_result = models.ForeignKey(HandgradingResult)


class AppliedAnnotation(ag_models.AutograderModel):
    comment = models.TextField(null=True,blank=True,default=None)

    location = models.OneToOneField(Location, related_name= 'location')

    annotation = models.ForeignKey(Annotation)

    handgrading_result = models.ForeignKey(HandgradingResult)

    def clean(self):
        if self.location.file_name not in self.handgrading_result.submission.submitted_filenames:
            raise ValidationError('Filename is not part of submitted files')


class Comment(ag_models.AutograderModel):
    location = models.OneToOneField(Location)

    text = models.TextField()

    handgrading_result = models.ForeignKey(HandgradingResult)


class ArbitraryPoints(ag_models.AutograderModel):
    location = models.OneToOneField(Location, related_name='location')

    text = models.TextField(null=True,blank=True,default=None)

    points = models.FloatField()

    handgrading_result = models.ForeignKey(HandgradingResult)

    def clean(self):
        if self.location.file_name not in self.handgrading_result.submission.submitted_filenames:
            raise ValidationError('Filename is not part of submitted files')


class Location(ag_models.AutograderModel):
    first_line = models.IntegerField()

    last_line = models.IntegerField()

    file_name = models.TextField(null=True,blank=True,default=None)

    def clean(self):
        errors = {}
        if self.last_line < self.first_line:
            raise  ValidationError('first line should be before last line')

