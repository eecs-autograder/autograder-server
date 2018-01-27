from django.core.validators import MaxValueValidator
from django.db import models

from autograder.core.fields import EnumField
from django.core import validators
from django.core.exceptions import ValidationError
from enum import Enum

from autograder.core.models import AutograderModel, Project, Submission, SubmissionGroup


class PointsStyle(Enum):
    """
    Ways handgrading points can be managed.

    Possible options:
        - start_at_zero_and_add: Each submission starts with a handgrading score of 0, and
            the sum of the point values for the Criterion items can increase the score until it
            reaches the total_possible_points.

        - start_at_max_and_subtract: Each submission starts off with the admin-defined max_points,
            and Criterion/Annotation items can be set/selected to reduce the total_points a student
            receives.
    """
    start_at_zero_and_add = "start_at_zero_and_add"
    start_at_max_and_subtract = "start_at_max_and_subtract"


class HandgradingRubric(AutograderModel):
    """
    Represents the rubric (which is linked to a project) used to configure handgrading settings.
    """
    project = models.OneToOneField(Project, related_name='handgrading_rubric',
                                   on_delete=models.CASCADE,
                                   help_text='''The Project this HandgradingRubric is 
                                   tied to. HandgradingRubrics are defined for each Project 
                                   individually.''')

    points_style = EnumField(PointsStyle, default=PointsStyle.start_at_zero_and_add, blank=True,
                             help_text='''The selected PointStyle for handgrading. Determines how 
                             total_points and total_possible_points are calculated. Can either
                             increase from zero to max_points or decrease from a set max_points to
                             zero.''')

    max_points = models.FloatField(blank=True, null=True, default=None,
                                   validators=[validators.MinValueValidator(0)],
                                   help_text='''The maximum value a handgrading score can reach
                                   (not accounting for extra points added later in 
                                   HandgradingResult via points_adjustment). This is set in one of
                                   two cases:
                                        - points_style is set to start_at_max_and_subtract, meaning 
                                          an admin user has to define the max_points to start at.
                                        - points_style is set to start_at_zero_and_add, and 
                                          admin wants to override the default max points, which is
                                          the sum of all the points of the defined criteria.''')

    show_grades_and_rubric_to_students = models.BooleanField(default=False, blank=True,
                                                             help_text='''Whether grades and rubric
                                                             is released to the students.''')

    handgraders_can_leave_comments = models.BooleanField(default=False, blank=True,
                                                         help_text='''Whether handgraders (defined
                                                         in Course) can leave comments on
                                                         submissions.''')

    handgraders_can_adjust_points = models.BooleanField(default=False, blank=True,
                                                        help_text='''Whether handgraders (defined 
                                                        in Course) can add or remove points 
                                                        arbitrarily in a submission. Can override
                                                        max_points upper limit.''')

    def clean(self):
        """
        Checks that max_points is not None when points_style is set to start_at_max_and_subtract.
        Throws ValidationError exception if this is the case.

        As defined by Django docs, "This method returns the clean data, which is then inserted
        into the cleaned_data dictionary of the form."
            source: https://docs.djangoproject.com/en/2.0/ref/forms/validation/
        """
        super().clean()

        if (self.points_style == PointsStyle.start_at_max_and_subtract and
                self.max_points is None):
            raise ValidationError(
                {'max_points':
                    'This field must not be None when "start at max" points style is chosen.'})

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
    Rubric item with fixed points that is not line specific.
    """
    handgrading_rubric = models.ForeignKey(HandgradingRubric, related_name='criteria',
                                           on_delete=models.CASCADE,
                                           help_text='''All criteria are tied to a specific 
                                           HandgradingRubric object, which itself are tied to a
                                           project.''')

    short_description = models.TextField(blank=True,
                                         help_text='''Provides a short description of
                                         the criterion item.''')

    long_description = models.TextField(blank=True,
                                        help_text='''Provides a long description of the criterion
                                        item. Used to explain the criterion item in more depth than 
                                        the short_description.''')

    points = models.FloatField(default=0, blank=True,
                               help_text='''The amount of points to add or subtract from a 
                               submission if its respective CriterionResult is selected or 
                               unselected respectively.''')

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
    Additional field that can be applied to a submission. Can be line specific.
    """
    handgrading_rubric = models.ForeignKey(HandgradingRubric, related_name='annotations',
                                           on_delete=models.CASCADE,
                                           help_text='''All annotations are tied to a specific
                                           HandgradingRubric object, which itself are tied to a 
                                           project.''')

    short_description = models.TextField(blank=True,
                                         help_text='''Provides a short description of the
                                         annotation item.''')

    long_description = models.TextField(blank=True,
                                        help_text='''Provides a long description of the annotation
                                        item.''')

    deduction = models.FloatField(default=0, blank=True, validators=[MaxValueValidator(0)],
                                  help_text='''The amount of points to deduct from a submission if
                                  its respective AppliedAnnotation is applied. This must be a
                                  number less than or equal to zero.''')

    max_deduction = models.FloatField(default=None, blank=True, null=True,
                                      validators=[MaxValueValidator(0)],
                                      help_text='''The maximum amount of points that can be
                                      deducted from a submission by applying this annotation. The 
                                      default value is None, and maximum value is zero.''')

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
    Represents the handgrading result of a group's best submission.
    """
    submission = models.OneToOneField(Submission, related_name='handgrading_result',
                                      on_delete=models.CASCADE,
                                      help_text='''The submission that the HandgradingResult is
                                      tied to.''')

    handgrading_rubric = models.ForeignKey(HandgradingRubric, related_name='handgrading_results',
                                           on_delete=models.CASCADE,
                                           help_text='''The HandgradingRubric tied to the
                                           HandgradingResult. This is where the HandgradingResult 
                                           gets the handgrading configuration details.''')

    submission_group = models.OneToOneField(SubmissionGroup, related_name='handgrading_result',
                                            on_delete=models.CASCADE,
                                            help_text='''The SubmissionGroup that submitted the
                                            submission that the HandgradingResult is tied to.''')

    finished_grading = models.BooleanField(default=False, blank=True,
                                           help_text='''Represents whether the HandgradingResult
                                           has been fully graded or if it still needs to be 
                                           completed. All HandgradingResult objects have this 
                                           boolean initially set to false.''')

    points_adjustment = models.FloatField(default=0, blank=True,
                                          help_text='''Represents any points added or removed from 
                                          a submission that are not tied to any Annotations or 
                                          Criteria.''')

    @property
    def submitted_filenames(self):
        """
        Returns a list of strings containing the filenames of the Submission the
        HandgradingRubric is tied to.
        """
        return self.submission.submitted_filenames

    @property
    def total_points(self):
        """
        Calculates and returns the total points a submission group earns for their submission
        as a result of their HandgradingResult (along with relevant CriterionResults and
        AppliedAnnotations).
        """
        total = 0
        if self.handgrading_rubric.points_style == PointsStyle.start_at_max_and_subtract:
            total = self.handgrading_rubric.max_points

        for annotation in Annotation.objects.filter(handgrading_rubric=self.handgrading_rubric):
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
        Calculates the total points a group can possibly earn for their submission as
        a result of their HandgradingResult (along with relevant CriterionResults and
        AppliedAnnotations).
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
    )

    EDITABLE_FIELDS = (
        'points_adjustment',
        'finished_grading',
    )


class CriterionResult(AutograderModel):
    """
    Tied to a Criterion object, specifies if such criterion is selected.
    """
    selected = models.BooleanField(
        help_text='''Specifies if the Criterion is selected or not. Used
           to determine whether the SubmissionGroup should be given
           the points specified by the Criterion or not.''')

    criterion = models.ForeignKey(Criterion, related_name='criterion_results',
                                  on_delete=models.CASCADE,
                                  help_text='''The Criterion that the CriterionResult is tied 
                                  to.''')

    handgrading_result = models.ForeignKey(HandgradingResult, related_name='criterion_results',
                                           on_delete=models.CASCADE,
                                           help_text='''The HandgradingResult the CriterionResult
                                           is tied to.''')

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
    was left with it.
    """
    # TODO: Needed?
    comment = models.TextField(blank=True)

    location = models.OneToOneField('Location', related_name='+',
                                    on_delete=models.PROTECT,
                                    help_text='''Defines the location where the Annotation
                                    was applied. Includes a filename, starting line number and
                                    ending line number, since annotations are applied on specific 
                                    lines in a specific file of a submission.''')

    annotation = models.ForeignKey(Annotation, on_delete=models.CASCADE,
                                   help_text='''The Annotation tied to the AppliedAnnotation.''')

    handgrading_result = models.ForeignKey(HandgradingResult, related_name='applied_annotations',
                                           on_delete=models.CASCADE,
                                           help_text='''The HandgradingResult tied to the 
                                           AppliedAnnotation.''')

    def clean(self):
        """
        Checks that the filename defined in the location is part of the submitted filename of the
        submission. Throws ValidationError exception if this is the case.

        As defined by Django docs, "This method returns the clean data, which is then inserted
        into the cleaned_data dictionary of the form."
            source: https://docs.djangoproject.com/en/2.0/ref/forms/validation/
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
    Comment left by staff or grader regarding submission. Can be applied to specific line.
    """
    location = models.OneToOneField('Location', related_name='+', null=True, blank=True,
                                    on_delete=models.PROTECT,
                                    help_text='''Specifies the Location of the comment, which 
                                    contains the first line, last line, and filename of where the 
                                    comment was applied. Specifying a location is optional.''')

    text = models.TextField(help_text='''Text that describes the comment.''')

    handgrading_result = models.ForeignKey(HandgradingResult, related_name='comments',
                                           on_delete=models.CASCADE,
                                           help_text='''The HandgradingResult that the Comment is
                                           tied to.''')

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
    Defined as a block of code within a specific file with a starting and ending line.
    """
    first_line = models.IntegerField(validators=[validators.MinValueValidator(0)],
                                     help_text='''The line number of the first line specified by
                                     the Location. Cannot take a value less than 0, since the
                                     first line of code in a file has a line number of 0.''')

    last_line = models.IntegerField(validators=[validators.MinValueValidator(0)],
                                    help_text='''The line number of the last line specified by
                                     the Location. Cannot take a value less than 0, since the
                                     first line of code in a file has a line number of 0. Can hold
                                     the same value as first_line if Location encompasses a single 
                                     line of code.''')

    filename = models.TextField(help_text='''Specifies the filename of the Location.''')

    def clean(self):
        """
        Checks that the first_line comes before (or is the same as) the last_line.
        Throws ValidationError exception if this is the case.

        As defined by Django docs, "This method returns the clean data, which is then inserted
        into the cleaned_data dictionary of the form."
            source: https://docs.djangoproject.com/en/2.0/ref/forms/validation/
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
