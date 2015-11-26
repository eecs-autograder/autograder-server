from django.db import models
from django.contrib.postgres.fields import ArrayField
from django.core.exceptions import ValidationError
from django.core.validators import MinValueValidator, MaxValueValidator

import autograder.shared.global_constants as gc
# import autograder.shared.utilities as ut

from autograder.models import Project
from autograder.models.utils import (
    PolymorphicModelValidatableOnSave, PolymorphicManagerWithValidateOnCreate,
    filename_matches_any_pattern)


class StudentTestSuiteBase(PolymorphicModelValidatableOnSave):
    """
    This base class provides a fat interface for evaluating student-submitted
    unit tests. To avoid dependencies with any particular unit testing
    framework, we've established a format for student test suites that
    can accomplish the same goals but is better suited to grading.
    We define a student-submitted test as follows:
        - A test is a single file containing a main() function or
            equivalent.
        - When the file is compiled/linked/interpreted/etc. together
            with the code module being tested, the student test file should
            exit with zero status if the test passes, and it should
            exit with any nonzero status if the test fails.
    Test cases are evaluated as follows:
    - For each test case (file) in the suite:
        - The test case is run with a correct implementation of
            the module being tested. If the test case exits with nonzero
            status (indicating test failure), the test will be considered
            invalid and will not be evaluated further.
        - If the test case correctly exited with zero status when run with
            the correct implementation, the test will then be run together
            with a set of specified buggy implementations of the module
            being tested. For each buggy implementation file:
                - Run the test case with the current buggy implementation file.
                    If the test case exits with nonzero status, record that
                    the test case correctly exposed the buggy implementation
                    as buggy.

    Fields:
        name -- The name used to identify this test suite.
                Must be non-empty and non-null.
                Must be unique among test cases associated
                with a given project.
                This field is REQUIRED.

        project -- The Project this test case is associated with.
                   This field is REQUIRED.

        student_test_case_filename_pattern -- A Project.FilePatternTuple
            object that specifies a pattern used to identify files that
            contain student test cases for this suite.
            This pattern MUST be one of the patterns specified by
            Project.expected_student_file_patterns
            This field is REQUIRED.

        correct_implementation_filename -- The name of a single project file
            that contains a correct (non-buggy) implementation of the module
            being tested by this test suite.
            This field is REQUIRED.

        buggy_implementation_filenames -- A list of names of project files,
            each of which contains a buggy implementation of the module
            being tested by this test suite.
            This field can be empty but may NOT be None
            Default value: Empty list

        implementation_file_alias -- When this value is non-empty, the current
            implementation file (buggy or correct) will be renamed to this
            value when it is to be run with the current test case.
            This field must adhere to the requirements of the function
            autograder.shared.utilities.check_user_provided_filename().
            Default value: empty string

            Example use case: If the module being tested is a templated C++
                class whose implementation is entirely in a header file,
                the student test cases will likely require that said header
                file has the same name every time.

        suite_resource_filenames -- A list of names of project files that
            must be present in the same directory as the current test case
            and buggy implementation. This includes source code dependencies,
            files that the program will read from/write to, etc.
            NOTE: This list should NOT include buggy implementation filenames.
            Those will be added automatically as per the evaluation protocol.

            This list is allowed to be empty.
            This value may NOT be None.
            Default value: empty list

            IMPORTANT: Each of these files must have been uploaded to the
                Project associated with this test case. Including a filename
                in this list that does not exist for the project will cause
                ValidationError to be raised.

        time_limit -- The time limit in seconds to be placed on each
            test case/buggy implementation pair.
            Must be > 0
            Must be <= 60
            Default value: autograder.shared.global_constants
                                     .DEFAULT_SUBPROCESS_TIMEOUT seconds

        hide_from_students -- When this field is True, students will not
            receive feedback about this test suite.
            Note: Staff members will still receive feedback on this test suite
                for their own submissions, but when viewing a student
                submission, this test suite will still be hidden.
            Default value: True

    Fat interface fields:
        TODO
        compiler --
        compiler_flags --
        suite_resource_files_to_compile_together --

        TODO
        interpreter --
        interpreter_flags --
    """
    class Meta:
        unique_together = ('name', 'project')

    objects = PolymorphicManagerWithValidateOnCreate()

    name = models.CharField(max_length=gc.MAX_CHAR_FIELD_LEN)
    project = models.ForeignKey('Project', related_name='student_test_suites')

    student_test_case_filename_pattern = models.CharField(
        max_length=gc.MAX_CHAR_FIELD_LEN)

    correct_implementation_filename = models.CharField(
        max_length=gc.MAX_CHAR_FIELD_LEN)

    buggy_implementation_filenames = ArrayField(
        models.CharField(
            max_length=gc.MAX_CHAR_FIELD_LEN,
            blank=True),
        default=list, blank=True)

    implementation_file_alias = models.CharField(
        max_length=gc.MAX_CHAR_FIELD_LEN, blank=True)

    suite_resource_filenames = ArrayField(
        models.CharField(
            max_length=gc.MAX_CHAR_FIELD_LEN,
            blank=True),
        default=list, blank=True)

    time_limit = models.IntegerField(
        default=gc.DEFAULT_SUBPROCESS_TIMEOUT,
        validators=[MinValueValidator(1),
                    MaxValueValidator(gc.MAX_SUBPROCESS_TIMEOUT)])

    hide_from_students = models.BooleanField(default=True)
