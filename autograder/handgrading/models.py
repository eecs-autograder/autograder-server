from django.core.validators import MaxValueValidator
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
    project = models.OneToOneField(Project, related_name='handgrading_rubric',
                                   on_delete=models.CASCADE)

    points_style = EnumField(PointsStyle, default=PointsStyle.start_at_zero_and_add, blank=True)

    max_points = models.IntegerField(blank=True, default=0,
                                     validators=[validators.MinValueValidator(0)])

    show_grades_and_rubric_to_students = models.BooleanField(default=False, blank=True)
    handgraders_can_leave_comments = models.BooleanField(default=False, blank=True)
    handgraders_can_adjust_points = models.BooleanField(default=False, blank=True)

    SERIALIZABLE_FIELDS = ('pk',
                           'last_modified',

                           'points_style',
                           'max_points',
                           'show_grades_and_rubric_to_students',
                           'handgraders_can_leave_comments',
                           'handgraders_can_adjust_points',

                           'project',
                           'criteria',
                           'annotations',)

    EDITABLE_FIELDS = ('points_style',
                       'max_points',
                       'show_grades_and_rubric_to_students',
                       'handgraders_can_leave_comments',
                       'handgraders_can_adjust_points',)

    SERIALIZE_RELATED = ('criteria',
                         'annotations',)


class Criterion(AutograderModel):
    """
    Rubric item with fixed points that is not line specific
    """
    handgrading_rubric = models.ForeignKey(HandgradingRubric, related_name='criteria',
                                           on_delete=models.CASCADE)

    short_description = models.TextField(blank=True)
    long_description = models.TextField(blank=True)

    points = models.FloatField(default=0, blank=True)

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
    handgrading_rubric = models.ForeignKey(HandgradingRubric, related_name='annotations',
                                           on_delete=models.CASCADE)

    short_description = models.TextField(blank=True)
    long_description = models.TextField(blank=True)

    deduction = models.FloatField(default=0, blank=True, validators=[MaxValueValidator(0)])
    max_deduction = models.FloatField(default=None, blank=True, null=True,
                                      validators=[MaxValueValidator(0)])

    SERIALIZABLE_FIELDS = (
        'pk',
        'handgrading_rubric',

        'short_description',
        'long_description',

        'deduction',
        'max_deduction',

        'last_modified',
    )

    EDITABLE_FIELDS = (
        'short_description',
        'long_description',
        'deduction',
        'max_deduction',
    )


class HandgradingResult(AutograderModel):
    """
    Tied to a specific submission
    """
    submission = models.OneToOneField(Submission, related_name='handgrading_result',
                                      on_delete=models.CASCADE)

    handgrading_rubric = models.ForeignKey(HandgradingRubric, related_name='handgrading_results',
                                           on_delete=models.CASCADE)

    submission_group = models.OneToOneField(SubmissionGroup, related_name='handgrading_result',
                                            on_delete=models.CASCADE)

    finished_grading = models.BooleanField(default=False, blank=True)
    points_adjustment = models.IntegerField(default=0, blank=True)

    @property
    def submitted_filenames(self):
        return self.submission.submitted_filenames

    SERIALIZABLE_FIELDS = (
        'pk',
        'last_modified',

        'submission',
        'handgrading_rubric',
        'submission_group',

        'applied_annotations',
        'comments',
        'criterion_results',

        'finished_grading',
        'points_adjustment',

        'submitted_filenames',
    )

    SERIALIZE_RELATED = (
        'applied_annotations',
        'comments',
        'criterion_results',

        'handgrading_rubric',
    )

    EDITABLE_FIELDS = (
        'points_adjustment',
        'finished_grading',
    )


class CriterionResult(AutograderModel):
    """
    Tied to a criterion object, specifies such criterion is selected
    """
    selected = models.BooleanField()

    criterion = models.ForeignKey(Criterion, related_name='criterion_results',
                                  on_delete=models.CASCADE)

    handgrading_result = models.ForeignKey(HandgradingResult, related_name='criterion_results',
                                           on_delete=models.CASCADE)

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

    location = models.OneToOneField('Location', related_name='+',
                                    on_delete=models.PROTECT)

    annotation = models.ForeignKey(Annotation, on_delete=models.CASCADE)

    handgrading_result = models.ForeignKey(HandgradingResult, related_name='applied_annotations',
                                           on_delete=models.CASCADE)

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
    location = models.OneToOneField('Location', related_name='+', null=True, blank=True,
                                    on_delete=models.PROTECT)

    text = models.TextField()

    handgrading_result = models.ForeignKey(HandgradingResult, related_name='comments',
                                           on_delete=models.CASCADE)

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
