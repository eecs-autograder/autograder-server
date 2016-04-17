import os
import shutil
import collections
import json
import copy

from django.db import models, transaction
from django.core import validators
from django.core import exceptions
import django.contrib.postgres.fields as psql_fields
from django.core import files

# from jsonfield import JSONField

from ..ag_model_base import AutograderModel
from ..semester import Semester

import autograder.utilities.fields as ag_fields

from ..autograder_test_case.autograder_test_case_base import (
    AutograderTestCaseBase)

import autograder.core.shared.global_constants as gc
import autograder.core.shared.utilities as ut


class Project(AutograderModel):
    """
    Represents a programming project for which students can
    submit solutions and have them evaluated.

    Fields:
        name -- The name used to identify this project.
                Must be non-empty and non-null.
                Must be unique among Projects associated with
                a given semester.
                This field is REQUIRED.

        semester -- The Semester this project belongs to.
            This field is REQUIRED.

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

        allow_submissions_from_non_enrolled_students -- By default,
            only staff members and enrolled students for a given Semester
            can submit to its Projects. When this field is set to True,
            submissions will be accepted from any authenticated Users,
            with the following caveats:
                - In order to view the Project, non-enrolled students
                must be given a direct link to a page where it can be viewed.
                - When group work is allowed, non-enrolled students can
                only be in groups with other non-enrolled students.
            Default value: False

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

            When ValidationError is raised for this field, the error message
            will be a list containing strings corresponding (in order) to
            each filename in this field. The strings will contain an error
            message for their corresponding filename or be empty if their
            corresponding filename did not cause an error.
            For example: a value for this field of ['spam', ''] would
            result in an error message along the lines of:
                ['', 'Filenames cannot be empty']

        expected_student_file_patterns -- A list of
            Project.FilePatternTuple objects describing
            Unix shell-style patterns that student-submitted files can match.

            Default value: empty list

            The pattern objects have the following fields:
                pattern --

                min_num_matches -- The minimum number of files students are
                    required to submit that match file_pattern.
                    This value must be non-negative.
                    This value must be <= max_num_matches.

                max_num_matches -- The maximum number of files students are
                    allowed to submit that match file_pattern.
                    This value must be non negative.
                    This value must be >= min_num_matches.

            TODO: simplify validation error format (just send back a list of
                strings corresponding to the objects)
            When ValidationError is raised for this field, the error message
            will be a list containing dictionaries *serialized as JSON strings*
            corresponding (in order) to each file pattern object in this field.
            If a given pattern did not cause any errors, its corresponding
            dictionary will be empty.
            Otherwise, the dictionary's key-value
            pairs will consist of <attribute>, <message> for each attribute
            in the pattern object. The <message> value will be an error
            message string if the attribute caused an error, otherwise
            <message> will be an empty string.
            For example, a value for this field of
                [('eggs*.txt', 1, 2), ('spam*.txt', 1, -1)]
            would result in an error message along the lines of:
                ['{}',
                 {'"pattern": "",
                  "min_num_matches": "",
                  "max_num_matches": "This value cannot be negative"''}]
            These dictionaries are serialized in order to get around
            the limitations of using ValidaitonError.

    Related object fields:
        autograder_test_cases -- The autograder test cases that belong to
            this Project.
        student_test_suites -- The student test suites that belong to
            this Project.

        expected_student_file_patterns --

    Properties:
        uploaded_filenames -- The names of files that have been uploaded
            to this Project.

    Instance methods:
        add_project_file()
        remove_project_file()
        update_project_file()

        get_project_file_basenames()
        get_project_files()
        get_file()
        has_file()

    Overridden methods:
        __init__()
        save()
        clean()
        delete()
    """
    # TODO: Replace with a ValidatedArrayField containing
    # JSONSerializableClassFields, make this named tuple a full class
    # that implements the JSONSerializable interface
    FilePatternTuple = collections.namedtuple(
        'FilePatternTuple',
        ['pattern', 'min_num_matches', 'max_num_matches'])

    class Meta:
        unique_together = ('name', 'semester')

    # -------------------------------------------------------------------------

    name = models.CharField(max_length=gc.MAX_CHAR_FIELD_LEN)
    semester = models.ForeignKey(Semester, related_name='projects')

    visible_to_students = models.BooleanField(default=False)
    closing_time = models.DateTimeField(default=None, null=True, blank=True)
    disallow_student_submissions = models.BooleanField(default=False)

    allow_submissions_from_non_enrolled_students = models.BooleanField(
        default=False)

    min_group_size = models.IntegerField(
        default=1, validators=[validators.MinValueValidator(1)])
    max_group_size = models.IntegerField(
        default=1, validators=[validators.MinValueValidator(1)])

    @property
    def uploaded_filenames(self):
        return tuple(self._uploaded_filenames)

    _uploaded_filenames = ag_fields.StringArrayField(blank=True, default=list)

    # @property
    # def required_student_files(self):
    #     return copy.deepcopy(self._required_student_files)

    # @required_student_files.setter
    # def required_student_files(self, value):
    #     files_removed = set(self._required_student_files) - set(value)

    #     for file_ in files_removed:
    #         tests_that_depend = AutograderTestCaseBase.objects.filter(
    #             student_resource_files__contains=[file_])
    #         if tests_that_depend:
    #             error_msg = (
    #                 'Cannot remove the required file: "{}". '
    #                 'The test cases {} depend on it.'.format(
    #                     file_,
    #                     ', '.join((test.name for test in tests_that_depend))
    #                 )
    #             )
    #             raise exceptions.ValidationError(
    #                 {'required_student_files': error_msg})

    #     self._required_student_files = value

    # _required_student_files = psql_fields.ArrayField(
    #     models.CharField(
    #         max_length=gc.MAX_CHAR_FIELD_LEN,
    #         blank=True  # We are setting this here so that the clean method
    #                     # can check for emptiness and throw a more specific
    #                     # error. This lets us send ValidationErrors
    #                     # to the GUI side in a more convenient format.
    #     ),
    #     default=list, blank=True
    # )

    # # TODO: fix this field so that there's a way to edit with the public
    # # interface
    # @property
    # def expected_student_file_patterns(self):
    #     return [
    #         Project.FilePatternTuple(obj[0], obj[1], obj[2])
    #         for obj in self._expected_student_file_patterns]

    # @expected_student_file_patterns.setter
    # def expected_student_file_patterns(self, value):
    #     old_patterns = {
    #         pat_obj.pattern for pat_obj in self.expected_student_file_patterns
    #     }

    #     new_patterns = {
    #         pat_obj.pattern if isinstance(pat_obj, Project.FilePatternTuple)
    #         else pat_obj[0]
    #         for pat_obj in value
    #     }

    #     removed_patterns = old_patterns - new_patterns

    #     for pattern in removed_patterns:
    #         tests_that_depend = AutograderTestCaseBase.objects.filter(
    #             student_resource_files__contains=[pattern])
    #         if tests_that_depend:
    #             error_msg = (
    #                 'Cannot remove the expected pattern: "{}". '
    #                 'The test cases {} depend on it.'.format(
    #                     pattern,
    #                     ', '.join((test.name for test in tests_that_depend))
    #                 )
    #             )
    #             raise exceptions.ValidationError(
    #                 {'expected_student_file_patterns': error_msg})

    #     self._expected_student_file_patterns = value

    # _expected_student_file_patterns = psql_fields.JSONField(
    #     default=list, blank=True)

    # -------------------------------------------------------------------------

    # def __init__(self, *args, **kwargs):
    #     patterns = kwargs.pop('expected_student_file_patterns', [])
    #     super().__init__(
    #         *args, _expected_student_file_patterns=patterns, **kwargs)

    def save(self, *args, **kwargs):
        if self.pk is None:
            self._uploaded_filenames = []

        super().save(*args, **kwargs)

        project_root_dir = ut.get_project_root_dir(self)
        project_files_dir = ut.get_project_files_dir(self)
        project_submissions_dir = ut.get_project_submission_groups_dir(
            self)

        if not os.path.isdir(project_root_dir):
            # Since the database is in charge of validating the uniqueness
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
        super().clean()

        if self.name:
            self.name = self.name.strip()

        errors = {}
        if not self.name:
            errors['name'] = "Name can't be empty"

        if self.max_group_size < self.min_group_size:
            errors['max_group_size'] = [
                'Maximum group size must be greater than '
                'or equal to minimum group size']

        # self.required_student_files = [
        #     filename.strip() for filename in self.required_student_files]

        # required_files_errors = []
        # req_files_error_found = False
        # for filename in self.required_student_files:
        #     try:
        #         ut.check_user_provided_filename(filename)

        #         num_occurrences = ut.count_if(
        #             self.required_student_files, lambda f: f == filename)
        #         if num_occurrences > 1:
        #             raise exceptions.ValidationError(
        #                 'Duplicates are not allowed')

        #         required_files_errors.append('')
        #     except exceptions.ValidationError as e:
        #         required_files_errors.append(e.messages)
        #         req_files_error_found = True

        # if req_files_error_found:
        #     errors['required_student_files'] = required_files_errors

        # file_pattern_errors = self._clean_expected_student_file_patterns()
        # if file_pattern_errors:
        #     errors['expected_student_file_patterns'] = file_pattern_errors

        if errors:
            raise exceptions.ValidationError(errors)

    # def _clean_expected_student_file_patterns(self):
    #     """
    #     Cleans self.expected_student_file_patterns and returns a
    #     dictionary of errors, if any. Returns None if no errors
    #     were found.
    #     """
    #     cleaned_patterns = []
    #     pattern_obj_errors = []
    #     pat_obj_err_found = False
    #     for pattern_obj in self.expected_student_file_patterns:
    #         cleaned_pattern = pattern_obj.pattern.strip()
    #         pattern_error = ''
    #         try:
    #             ut.check_shell_style_file_pattern(cleaned_pattern)
    #             num_occurrences = ut.count_if(
    #                 self.expected_student_file_patterns,
    #                 lambda pat_tup: pat_tup.pattern == cleaned_pattern)
    #             if num_occurrences > 1:
    #                 raise exceptions.ValidationError(
    #                     'Duplicate patterns are not allowed')
    #         except exceptions.ValidationError as e:
    #             pattern_error = e.messages

    #         cleaned_min = pattern_obj.min_num_matches
    #         min_error = ''
    #         try:
    #             cleaned_min = int(pattern_obj.min_num_matches)

    #             if cleaned_min < 0:
    #                 min_error = 'This value cannot be negative'
    #         except ValueError as e:
    #             min_error = 'This value must be an integer'

    #         cleaned_max = pattern_obj.max_num_matches
    #         max_error = ''
    #         try:
    #             cleaned_max = int(pattern_obj.max_num_matches)

    #             if cleaned_max < 0:
    #                 max_error = 'This value cannot be negative'

    #             if not min_error and cleaned_max < cleaned_min:
    #                 max_error = (
    #                     'Maximum number of matches must be less than or '
    #                     'equal to minimum number of matches')
    #         except ValueError as e:
    #             max_error = 'This value must be an integer'

    #         cleaned_patterns.append(
    #             [cleaned_pattern, cleaned_min, cleaned_max])
    #         if pattern_error or min_error or max_error:
    #             pat_obj_err_found = True
    #             pattern_obj_errors.append(
    #                 json.dumps(
    #                     {'pattern': pattern_error,
    #                      'min_num_matches': min_error,
    #                      'max_num_matches': max_error}))
    #         else:
    #             pattern_obj_errors.append(json.dumps({}))

    #     self._expected_student_file_patterns = cleaned_patterns
    #     if pat_obj_err_found:
    #         return pattern_obj_errors

    #     return None

    # -------------------------------------------------------------------------

    def delete(self, *args, **kwargs):
        project_root_dir = ut.get_project_root_dir(self)
        super().delete(*args, **kwargs)

        shutil.rmtree(project_root_dir)

    # -------------------------------------------------------------------------

    def add_project_file(self, uploaded_file):
        """
        Adds the given file to this Project.

        If a file with the same name already exists, ValidationError
        will be raised.
        """
        with transaction.atomic():
            Project.objects.select_for_update().get(pk=self.pk)
            # print(uploaded_file.name)
            ut.check_user_provided_filename(uploaded_file.name)
            if uploaded_file.name in self._uploaded_filenames:
                raise exceptions.ValidationError(
                    'File exists: {}'.format(uploaded_file.name))
            self._uploaded_filenames.append(uploaded_file.name)

            full_path = self._get_project_file_dir(
                uploaded_file.name)
            with open(full_path, 'wb') as f:
                for chunk in uploaded_file.chunks():
                    f.write(chunk)

            self.save()
        # self._project_files.add(
        #     _UploadedProjectFile.objects.validate_and_create(
        #         uploaded_file=uploaded_file, project=self))

    def remove_project_file(self, filename):
        """
        Removes the specified file from the database and filesystem.

        Raises ObjectDoesNotExist if no such file exists for this Project.

        Raises ValidationError if the file is depended on by any test
        cases belonging to this Project, i.e. if it is listed in
        project.test_resource_files
        """
        self._check_file_exists(filename)

        tests_depend_on_file = self.autograder_test_cases.filter(
            test_resource_files__contains=[filename])
        if tests_depend_on_file:
            raise exceptions.ValidationError(
                "One or more test cases depend on file " + filename)

        with transaction.atomic():
            Project.objects.select_for_update().get(pk=self.pk)
            self._uploaded_filenames.remove(filename)
            with ut.ChangeDirectory(ut.get_project_files_dir(self)):
                os.remove(filename)
            self.save()

    def update_project_file(self, filename, new_contents):
        self._check_file_exists(filename)

        with transaction.atomic():
            Project.objects.select_for_update().get(pk=self.pk)
            full_path = self._get_project_file_dir(filename)
            with open(full_path, 'w') as f:
                f.write(new_contents)

            self.save()
        # file_ = self._get_uploaded_file(filename)
        # print(type(file_.uploaded_file))
        # file_.uploaded_file.open('wb')
        # file_.uploaded_file.write(new_contents)

    # def _get_uploaded_file(self, filename):
    #     full_path = os.path.join(
    #         ut.get_project_files_relative_dir(self), filename)
    #     return _UploadedProjectFile.objects.get(
    #         project=self, uploaded_file=full_path)

    def get_file(self, filename):
        self._check_file_exists(filename)
        return files.File(
            open(self._get_project_file_dir(filename)),
            name=os.path.basename(filename))

    def get_project_files(self):
        """
        Returns an iterable of this project's uploaded files
        (as django-style file-like objects).
        """
        return (self.get_file(filename) for
                filename in self._uploaded_filenames)
        # return [obj.uploaded_file for obj in self._project_files.all()]

    def get_project_file_basenames(self):
        """
        Returns a list of this project's uploaded file basenames.
        """
        return self.uploaded_filenames

    def has_file(self, filename):
        return filename in self._uploaded_filenames

    def _get_project_file_dir(self, filename):
        return os.path.join(
            ut.get_project_files_dir(self), filename)

    def _check_file_exists(self, filename):
        if filename not in self._uploaded_filenames:
            raise exceptions.ObjectDoesNotExist(
                "File {0} for {1} {2} project {3} does not exist".format(
                    filename,
                    self.semester.course.name, self.semester.name,
                    self.name))
