from django.core.validators import MaxValueValidator
from django.db import models

from autograder.core.fields import EnumField
from django.core import validators
from django.core.exceptions import ValidationError
from enum import Enum

from autograder.core.models import AutograderModel, Project, Submission, SubmissionGroup


class PointsStyle(Enum):
    """
    Specifies how handgrading scores should be initialized.

    Values:
        - start_at_zero_and_add: The handgrading score for a group starts at 0 and
            points are added to the total. Total points possible is the sum of
            the point values for non-negative Criteria.

        - start_at_max_and_subtract: The handgrading score for a group starts at
            HandgradingRubric.max_points. Total points possible is fixed at this
            value.
    """
    start_at_zero_and_add = "start_at_zero_and_add"
    start_at_max_and_subtract = "start_at_max_and_subtract"


class HandgradingRubric(AutograderModel):
    """
    Contains general settings for handgrading.
    """
    project = models.OneToOneField(
        Project, related_name='handgrading_rubric', on_delete=models.CASCADE,
        help_text="The Project this HandgradingRubric belongs to.")

    points_style = EnumField(
        PointsStyle, default=PointsStyle.start_at_zero_and_add, blank=True,
        help_text='''Determines how total_points and total_possible_points are calculated
                     for HandgradingResults.''')

    max_points = models.FloatField(
        blank=True, null=True, default=None, validators=[validators.MinValueValidator(0)],
        help_text='''The denominator of a handgrading score.
                     When points_style is "start_at_zero_and_add", this value
                     overrides the sum of positive Criteria point values as the
                     total points possible.
                     When points_style is "start_at_max_and_subtract", this field
                     is REQUIRED.''')

    show_grades_and_rubric_to_students = models.BooleanField(
        default=False, blank=True,
        help_text='''Whether students can see their handgrading scores,
                     including information from the rubric.''')

    handgraders_can_leave_comments = models.BooleanField(
        default=False, blank=True,
        help_text='''Whether handgraders can add comments to a HandgradingResult.''')

    handgraders_can_adjust_points = models.BooleanField(
        default=False, blank=True,
        help_text='''Whether handgraders can edit HandgradingResult.point_adjustment.''')

    def clean(self):
        """
        Checks that max_points is not None when points_style
        is set to start_at_max_and_subtract.
        """
        super().clean()

        if (self.points_style == PointsStyle.start_at_max_and_subtract and
                self.max_points is None):
            raise ValidationError(
                {'max_points':
                    'This field must not be None when "start at max" points style is chosen.'})

    SERIALIZABLE_FIELDS = ('pk',
                           'project',
                           'last_modified',

                           'points_style',
                           'max_points',
                           'show_grades_and_rubric_to_students',
                           'handgraders_can_leave_comments',
                           'handgraders_can_adjust_points',

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
    A "checkbox" rubric item.
    """
    class Meta:
        order_with_respect_to = 'handgrading_rubric'

    handgrading_rubric = models.ForeignKey(
        HandgradingRubric, related_name='criteria', on_delete=models.CASCADE,
        help_text='''The rubric this Criterion belongs to.''')

    short_description = models.TextField(
        blank=True,
        help_text='''A short description of this Criterion.''')

    long_description = models.TextField(
        blank=True,
        help_text='''A long description of this Criterion. Note that there is no
                     enforced length difference between short_ and long_description.
                     The separation is purely to be used by clients.''')

    points = models.FloatField(
        default=0, blank=True,
        help_text='''The amount of points to add or subtract from a handgrading score
                     when selected.''')

    SERIALIZABLE_FIELDS = ('pk',
                           'handgrading_rubric',
                           'last_modified',

                           'short_description',
                           'long_description',
                           'points',)

    EDITABLE_FIELDS = ('short_description',
                       'long_description',
                       'points',)


class Annotation(AutograderModel):
    """
    A pre-defined comment that can be applied to specific lines of code, with
    an optional deduction attached.
    """
    class Meta:
        order_with_respect_to = 'handgrading_rubric'

    handgrading_rubric = models.ForeignKey(
        HandgradingRubric, related_name='annotations', on_delete=models.CASCADE,
        help_text='''The HandgradingRubric this Annotation belongs to.''')

    short_description = models.TextField(blank=True,
                                         help_text='''A short description of this Annotation.''')

    long_description = models.TextField(
        blank=True,
        help_text='''A long description of this Criterion. Note that there is no
                     enforced length difference between short_ and long_description.
                     The separation is purely to be used by clients.''')

    deduction = models.FloatField(
        default=0, blank=True, validators=[MaxValueValidator(0)],
        help_text='''The amount of points to deduct from a handgrading score when
                     applied. Must be non-positive.''')

    max_deduction = models.FloatField(
        default=None, blank=True, null=True, validators=[MaxValueValidator(0)],
        help_text='''The maximum amount of points that can be cumulatively
                     deducted from a handgrading score by applications of
                     this annotation. Must be None or non-positive.''')

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
    Contains general information about a group's handgrading result
    Represents the handgrading result of a group's best submission.
    """
    submission_group = models.OneToOneField(
        SubmissionGroup, related_name='handgrading_result', on_delete=models.CASCADE,
        help_text='''The SubmissionGroup that this HandgradingResult is for.''')

    submission = models.OneToOneField(
        Submission, related_name='handgrading_result', on_delete=models.CASCADE,
        help_text='''The specific submission that is being handgraded.''')

    handgrading_rubric = models.ForeignKey(
        HandgradingRubric, related_name='handgrading_results', on_delete=models.CASCADE,
        help_text='''The HandgradingRubric that this HandgradingResult is based on.''')

    finished_grading = models.BooleanField(
        default=False, blank=True,
        help_text='''Handgraders should set this field to True when they are finished
                     grading this group's submission.''')

    points_adjustment = models.FloatField(
        default=0, blank=True,
        help_text='''An arbitrary adjustment to this result's total points.
                     Note that this does not affect total points possible.''')

    @property
    def submitted_filenames(self):
        """
        Returns a list of strings containing the filenames of the Submission this result
        belongs to.
        """
        return self.submission.submitted_filenames

    @property
    def total_points(self):
        """
        Returns the total number of points awarded. Note that it is possible
        for this value to be greater than total_points.
        """
        total = 0
        if self.handgrading_rubric.points_style == PointsStyle.start_at_max_and_subtract:
            total = self.handgrading_rubric.max_points

        for annotation in self.handgrading_rubric.annotations.all():
            total_for_annotation = 0
            # Using Python filter() instead of Django queryset filter()
            # to allow prefetching.
            applied_annotations = filter(lambda appl_annot: appl_annot.annotation == annotation,
                                         self.applied_annotations.all())
            for applied_annotation in applied_annotations:
                total_for_annotation += applied_annotation.annotation.deduction

            if annotation.max_deduction and total_for_annotation < annotation.max_deduction:
                total += annotation.max_deduction
            else:
                total += total_for_annotation

        total += sum(criterion_result.criterion.points for
                     criterion_result in self.criterion_results.all() if criterion_result.selected)

        total += self.points_adjustment
        return max(0, total)

    @property
    def total_points_possible(self):
        """
        Returns the denominator of the handgrading score based on the
        handgrading rubric's points style and max points.
        """
        if self.handgrading_rubric.max_points is not None:
            return self.handgrading_rubric.max_points

        return sum(criterion.points for criterion in
                   self.handgrading_rubric.criteria.all() if criterion.points >= 0)

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
        'total_points',
        'total_points_possible'
    )

    SERIALIZE_RELATED = (
        'applied_annotations',
        'comments',
        'criterion_results',

        'handgrading_rubric',

        'submission_group',
    )

    EDITABLE_FIELDS = (
        'points_adjustment',
        'finished_grading',
    )


class CriterionResult(AutograderModel):
    """
    Specifies whether a handgrading criterion was selected (i.e. the checkbox was checked).
    """
    class Meta:
        ordering = ('criterion___order',)

    selected = models.BooleanField(
        help_text='''When True, indicates that the criterion's point allotment should be
                     added to (or subtracted from if negative) the total handgrading points.''')

    criterion = models.ForeignKey(
        Criterion, related_name='criterion_results', on_delete=models.CASCADE,
        help_text='''The Criterion that the CriterionResult is tied to.''')

    handgrading_result = models.ForeignKey(
        HandgradingResult, related_name='criterion_results', on_delete=models.CASCADE,
        help_text='''The HandgradingResult this CriterionResult belongs to.''')

    SERIALIZABLE_FIELDS = ('pk',
                           'last_modified',

                           'selected',
                           'criterion',
                           'handgrading_result',)

    EDITABLE_FIELDS = ('selected',)

    SERIALIZE_RELATED = ('criterion',)


class AppliedAnnotation(AutograderModel):
    """
    Represents a single instance of adding an annotation to student source code.
    """
    annotation = models.ForeignKey(
        Annotation, on_delete=models.CASCADE,
        help_text='''The Annotation that was applied to the source code.''')

    handgrading_result = models.ForeignKey(
        HandgradingResult, related_name='applied_annotations', on_delete=models.CASCADE,
        help_text='''The HandgradingResult the applied annotation belongs to.''')

    location = models.OneToOneField(
        'Location', related_name='+', on_delete=models.PROTECT,
        help_text='''The source code location where the Annotation was applied.''')

    comment = models.TextField(blank=True, help_text="REMOVE ME")

    def clean(self):
        """
        Checks that the filename specified in the location is actually one of
        the files in the submission.
        """
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
    A custom comment that can either apply to the whole submission or a specific
    location in the source code.
    """
    class Meta:
        ordering = ('pk',)

    location = models.OneToOneField(
        'Location', related_name='+', null=True, blank=True, on_delete=models.PROTECT,
        help_text='''When not None, specifies the source code location this comment
                     applies to.''')

    text = models.TextField(help_text='''Text to be shown to students.''')

    handgrading_result = models.ForeignKey(
        HandgradingResult, related_name='comments', on_delete=models.CASCADE,
        help_text='''The HandgradingResult that this Comment belongs to.''')

    def clean(self):
        """
        Checks that the filename defined in the location (if a location is defined) is part of the
        submitted filenames of the submission. Throws ValidationError exception if this is the
        case.

        As defined by Django docs, "This method returns the clean data, which is then inserted
        into the cleaned_data dictionary of the form."
            source: https://docs.djangoproject.com/en/2.0/ref/forms/validation/
        """
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
    A region of source code in a specific file with a starting and ending line.
    """
    filename = models.TextField(help_text='''The file that contains the source code region.''')

    first_line = models.IntegerField(
        validators=[validators.MinValueValidator(0)],
        help_text='''The first line in the source code region. Must be non-negative.''')

    last_line = models.IntegerField(
        validators=[validators.MinValueValidator(0)],
        help_text='''The last line in the source code region (inclusive). Must be non-negative.''')

    def clean(self):
        """
        Checks that first_line <= last_line.
        """
        if self.last_line is not None and (self.last_line < self.first_line):
            raise ValidationError('first line should be before last line')

    SERIALIZABLE_FIELDS = ('pk',
                           'last_modified',

                           'first_line',
                           'last_line',
                           'filename',)

    EDITABLE_FIELDS = ('first_line',
                       'last_line',)
