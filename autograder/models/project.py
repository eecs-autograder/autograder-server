from django.db import models
from django.core.exceptions import ValidationError

from picklefield.fields import PickledObjectField

from autograder.models.model_utils import ModelValidatedOnSave
from autograder.models import Semester

from autograder.shared import global_constants as gc


class Project(ModelValidatedOnSave):
    """
    Represents a programming project for which students can
    submit solutions and have them evaluated.

    Primary key: composite based on this Project's name and Semester.

    Fields:
        name -- The name used to identify this project.
                Must be non-empty and non-null.
                Must be unique among Projects associated with
                a given semester.
                This field is REQUIRED.

        semester -- The Semester this project belongs to.
            This field is REQUIRED.

        project_files -- A list of names of files that have been uploaded
            for this Project. For example, these files might include
            C++ header files, libraries that are provided to students,
            autograder test cases, input files, etc.
            Default value: empty list

        visible_to_students -- Whether information about this Project can
            be viewed by students.
            Default value: False

        closing_time -- The date and time that this project should stop
            accepting submissions.
            A value of None indicates that this project should stay open.
            Default value: None

        disallow_student_submissions -- A hard override that will prevent
            students from submitting even if visible_to_students is True and
            it is before closing_time.
            Default value: False.

        min_group_size -- The minimum number of students that can work
            in a group on this project.
            Must be >= 1.
            Must be <= max_group_size.
            Default value: 1

        max_group_size -- The maximum number of students that can work
            in a group on this project.
            Must be >= 1.
            Must be >= min_group_size.
            Default value: 1

        required_student_files -- A list of files that students
            are required to submit for this project.
            Default value: empty list

        expected_student_file_patterns -- A dictionary of Unix shell-style
            patterns that files students submit can match.
            Default value: empty dictionary

            The key, value pairs are as follows:

            {
                file_pattern: [min_num_matches, max_num_matches]
            }

            file_pattern should be a shell-style file pattern suitable for
                use with Python's fnmatch.fnmatch()
                function (https://docs.python.org/3.4/library/fnmatch.html).

            min_num_matches is the minimum number of files students are
                required to submit that match file_pattern.
                This value must be non-negative.
                This value must be <= max_num_matches.

            max_num_matches is the maximum number of files students are
                allowed to submit that match file_pattern.
                This value must be non negative.
                This value must be >= min_num_matches.

    Instance methods:
        add_project_file() TODO
        remove_project_file() TODO
        rename_project_file() TODO?

    Static methods:
        get_by_composite_key()

    Overridden methods:
        validate_fields()
    """
    name = models.CharField(max_length=gc.MAX_CHAR_FIELD_LEN)
    semester = models.ForeignKey(Semester)

    @property
    def project_files(self):
        return self._project_files

    visible_to_students = models.BooleanField(default=False)
    closing_time = models.DateTimeField(default=None, null=True)
    disallow_student_submissions = models.BooleanField(default=False)
    min_group_size = models.IntegerField(default=1)
    max_group_size = models.IntegerField(default=1)
    required_student_files = PickledObjectField(default=[])
    expected_student_file_patterns = PickledObjectField(default={})

    _project_files = PickledObjectField(default=[])

    _composite_primary_key = models.TextField(primary_key=True)

    # -------------------------------------------------------------------------
    # -------------------------------------------------------------------------

    @staticmethod
    def get_by_composite_key(project_name, semester):
        """
        Does a key lookup for and returns the Project with the given
        name and that belongs to the specified semester.
        """
        return Project.objects.get(
            pk=Project._compute_composite_primary_key(project_name, semester))

    @staticmethod
    def _compute_composite_primary_key(project_name, semester):
        return "{0}_{1}_{2}".format(
            semester.course.name, semester.name, project_name)

    # -------------------------------------------------------------------------

    def validate_fields(self):
        if not self.pk:
            self._composite_primary_key = self._compute_composite_primary_key(
                self.name, self.semester)

        if not self.name:
            raise ValidationError(
                "Project names must be non-null and non-empty")

        # Foreign key fields raise ValueError if you try to
        # assign a null value to them, so an extra check for semester
        # is not needed.

        if not self._composite_primary_key:
            raise Exception("Invalid composite primary key")

        if self.min_group_size < 1:
            raise ValidationError("Minimum group size must be at least 1")

        if self.max_group_size < 1:
            raise ValidationError("Maximum group size must be at least 1")

        if self.max_group_size < self.min_group_size:
            raise ValidationError(
                "Maximum group size must be >= minimum group size")

        for filename in self.required_student_files:
            if not filename:
                raise ValidationError(
                    "The empty string is not a valid filename")

        for file_pattern, min_max in self.expected_student_file_patterns.items():
            if not file_pattern:
                raise ValidationError(
                    "The empty string is not a valid file pattern")

            if min_max[0] > min_max[1]:
                raise ValidationError(
                    "The minimum for an expected file pattern must be less "
                    "than the maximum")

            if min_max[0] < 0:
                raise ValidationError(
                    "The minimum for an expected file pattern "
                    "must be non-negative")

            if min_max[1] < 0:
                raise ValidationError(
                    "The maximum for an expected file pattern "
                    "must be non-negative")
