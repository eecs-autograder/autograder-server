import os
import collections

from django.db import models
from django.core.validators import MinValueValidator
from django.core.exceptions import ValidationError

# from jsonfield import JSONField

from autograder.models.model_utils import (
    ModelValidatableOnSave, ManagerWithValidateOnCreate)
from autograder.models import Semester

import autograder.shared.global_constants as gc
import autograder.shared.utilities as ut


ExpectedStudentFilePatternTuple = collections.namedtuple(
    'ExpectedStudentFile',
    ['pattern', 'min_num_matches', 'max_num_matches'])


class Project(ModelValidatableOnSave):
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
            See autograder.shared.utilities.check_user_provided_filename
            for restrictions on filenames.
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
            See autograder.shared.utilities.check_user_provided_filename
            for restrictions on filenames.
            Default value: empty list

        expected_student_file_patterns -- A list of objects encapsulating
            Unix shell-style patterns that student-submitted files can match.
            Default value: empty list

            The pattern objects have the following fields:
                pattern -- A string containing the actual pattern.
                    This should be a shell-style file pattern suitable for
                    use with Python's fnmatch.fnmatch()
                    function (https://docs.python.org/3.4/library/fnmatch.html)

                min_num_matches -- The minimum number of files students are
                    required to submit that match file_pattern.
                    This value must be non-negative.
                    This value must be <= max_num_matches.

                max_num_matches -- The maximum number of files students are
                    allowed to submit that match file_pattern.
                    This value must be non negative.
                    This value must be >= min_num_matches.

    Instance methods:
        add_project_file()
        remove_project_file()
        rename_project_file() TODO?

        add_required_student_file()
        get_required_student_filenames()

        add_expected_student_file_pattern()

        add_test_case() TODO (here or in test case?)
        update_test_case() TODO (here or in test case?)
        remove_test_case() TODO (here or in test case?)

    Overridden methods:
        save()
        clean()
    """
    class Meta:
        unique_together = ('name', 'semester')

    objects = ManagerWithValidateOnCreate()

    # -------------------------------------------------------------------------

    name = models.CharField(max_length=gc.MAX_CHAR_FIELD_LEN)
    semester = models.ForeignKey(Semester)

    # @property
    # def project_files(self):
    #     return self._project_files

    # _project_files = JSONField(default=[])
    visible_to_students = models.BooleanField(default=False)
    closing_time = models.DateTimeField(default=None, null=True, blank=True)
    disallow_student_submissions = models.BooleanField(default=False)
    min_group_size = models.IntegerField(
        default=1, validators=[MinValueValidator(1)])
    max_group_size = models.IntegerField(
        default=1, validators=[MinValueValidator(1)])

    # required_student_files = JSONField(default=[])
    # expected_student_file_patterns = JSONField(default={})

    # _composite_primary_key = models.TextField(primary_key=True)

    # -------------------------------------------------------------------------
    # -------------------------------------------------------------------------

    def add_project_file(self, uploaded_file):
        """
        Adds the given file to this Project.

        If a file with the same name already exists, the new file is
        renamed by adding a short, random string to the filename. (This
        is the default behavior in django.)
        """
        self.project_files.add(
            _UploadedProjectFile.objects.validate_and_create(
                uploaded_file=uploaded_file, project=self.project))
        # ut.check_user_provided_filename(filename)

        # if filename in self._project_files and not overwrite_ok:
        #     raise FileExistsError(
        #         "File {0} for {1} {2} project {3} already exists".format(
        #             filename,
        #             self.semester.course.name, self.semester.name,
        #             self.name))

        # self._project_files.append(filename)
        # self.save()

        # with ut.ChangeDirectory(ut.get_project_files_dir(self)):
        #     with open(filename, 'w') as f:
        #         f.write(file_content)

    # -------------------------------------------------------------------------

    def remove_project_file(self, filename):
        """
        Removes the specified file from the database and filesystem.

        Raises FileNotFoundError if no such file exists for this Project.

        Note that atomicity for this operation is handled at the
        request level.
        """
        if filename not in self._project_files:
            raise FileNotFoundError(
                "File {0} for {1} {2} project {3} does not exist".format(
                    filename,
                    self.semester.course.name, self.semester.name,
                    self.name))

        self._project_files.remove(filename)
        self.save()

        with ut.ChangeDirectory(ut.get_project_files_dir(self)):
            os.remove(filename)

    # -------------------------------------------------------------------------

    def get_project_files(self):
        """
        Returns a list of this project's uploaded files
        (as django-style file-like objects).
        """
        return [obj.uploaded_file for obj in self.project_files.all()]

    # -------------------------------------------------------------------------

    def add_required_student_file(self, filename):
        """
        Adds the given filename to the list of files that students
        are required to submit for this project.
        """
        self.required_student_files.add(
            _RequiredStudentFile.objects.validate_and_create(
                filename=filename,
                project=self))

    # -------------------------------------------------------------------------

    def get_required_student_filenames(self):
        """
        Returns a list of filenames that students are required to submit
        for this project.
        """
        return [obj.filename for obj in self.required_student_files.all()]

    # -------------------------------------------------------------------------

    def add_expected_student_file_pattern(self, pattern,
                                          min_matches, max_matches):
        """
        Adds the given pattern with the specified min and max to the
        list of patterns that student-submitted files can match.
        """
        self.expected_student_file_patterns.add(
            _ExpectedStudentFilePattern.objects.validate_and_create(
                pattern=pattern,
                min_num_matches=min_matches,
                max_num_matches=max_matches,
                project=self))

    # -------------------------------------------------------------------------

    def get_expected_student_file_patterns(self):
        """
        Returns a list of named tuples representing patterns that
        student-submitted files can match.
        The tuples contain the following fields:
            pattern
            min_num_matches
            max_num_matches
        See Project.expected_student_file_patterns for more information
        on these fields.
        """
        return [
            ExpectedStudentFilePatternTuple(
                obj.pattern, obj.min_num_matches, obj.max_num_matches)
            for obj in self.expected_student_file_patterns.all()]

    # -------------------------------------------------------------------------

    def save(self, *args, **kwargs):
        super().save(*args, **kwargs)

        project_root_dir = ut.get_project_root_dir(self)
        project_files_dir = ut.get_project_files_dir(self)
        project_submissions_dir = ut.get_project_submissions_by_student_dir(
            self)

        if not os.path.isdir(project_root_dir):
            # Since the database is in charge or validating the uniqueness
            # of this project, we can assume at this point that creating
            # the project directories will succeed.
            # If for some reason it fails, this will be considered a
            # more severe error, and the OSError thrown by os.makedirs
            # will be handled at a higher level.

            os.makedirs(project_root_dir)
            os.mkdir(project_files_dir)
            os.mkdir(project_submissions_dir)

    # -------------------------------------------------------------------------

    def clean(self):
        if self.max_group_size < self.min_group_size:
            raise ValidationError(
                {'max_group_size': ['Maximum group size must be greater than '
                                    'or equal to minimum group size']})

    # -------------------------------------------------------------------------

    # def validate_fields(self):
    #     if not self.pk:
    #         self._composite_primary_key = self._compute_composite_primary_key(
    #             self.name, self.semester)

    #     if not self.name:
    #         raise ValueError(
    #             "Project names must be non-null and non-empty")

    #     # Foreign key fields raise ValueError if you try to
    #     # assign a null value to them, so an extra check for semester
    #     # is not needed.

    #     if not self._composite_primary_key:
    #         raise Exception("Invalid composite primary key")

    #     if self.min_group_size < 1:
    #         raise ValueError("Minimum group size must be at least 1")

    #     if self.max_group_size < 1:
    #         raise ValueError("Maximum group size must be at least 1")

    #     if self.max_group_size < self.min_group_size:
    #         raise ValueError(
    #             "Maximum group size must be >= minimum group size")

    #     for filename in self.required_student_files:
    #         ut.check_user_provided_filename(filename)

    #     for file_pattern, min_max in self.expected_student_file_patterns.items():
    #         ut.check_shell_style_file_pattern(file_pattern)

    #         if min_max[0] > min_max[1]:
    #             raise ValueError(
    #                 "The minimum for an expected file pattern must be less "
    #                 "than the maximum")

    #         if min_max[0] < 0:
    #             raise ValueError(
    #                 "The minimum for an expected file pattern "
    #                 "must be non-negative")

    #         if min_max[1] < 0:
    #             raise ValueError(
    #                 "The maximum for an expected file pattern "
    #                 "must be non-negative")


# -----------------------------------------------------------------------------
# -----------------------------------------------------------------------------
# -----------------------------------------------------------------------------

def _get_project_file_upload_to_dir(instance, filename):
    return os.path.join(
        ut.get_project_files_relative_dir(instance.project), filename)


def _validate_filename(file_obj):
    ut.check_user_provided_filename(file_obj.name)


class _UploadedProjectFile(ModelValidatableOnSave):
    objects = ManagerWithValidateOnCreate()

    project = models.ForeignKey(Project, related_name='project_files')
    uploaded_file = models.FileField(
        upload_to=_get_project_file_upload_to_dir,
        validators=[_validate_filename])


# -----------------------------------------------------------------------------

class _RequiredStudentFile(ModelValidatableOnSave):
    class Meta:
        unique_together = ('project', 'filename')

    objects = ManagerWithValidateOnCreate()

    project = models.ForeignKey(Project, related_name='required_student_files')
    filename = models.CharField(
        max_length=gc.MAX_CHAR_FIELD_LEN,
        validators=[ut.check_user_provided_filename])


# -----------------------------------------------------------------------------

class _ExpectedStudentFilePattern(ModelValidatableOnSave):
    class Meta:
        unique_together = ('project', 'pattern')

    objects = ManagerWithValidateOnCreate()

    project = models.ForeignKey(
        Project, related_name='expected_student_file_patterns')

    pattern = models.CharField(
        max_length=gc.MAX_CHAR_FIELD_LEN,
        validators=[ut.check_shell_style_file_pattern])
    min_num_matches = models.IntegerField(validators=[MinValueValidator(0)])
    max_num_matches = models.IntegerField(validators=[MinValueValidator(0)])

    def clean(self):
        super().clean()

        if self.min_num_matches > self.max_num_matches:
            raise ValidationError(
                {'min_num_matches':
                 ['Minimum number of matches must be less than or equal '
                  'to maximum number of matches']})
