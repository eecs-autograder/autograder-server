from django.db import models
from django.contrib.postgres.fields import ArrayField
from django.core.exceptions import ValidationError
from django.core.validators import MinValueValidator, MaxValueValidator, RegexValidator

import autograder.core.shared.global_constants as gc
import autograder.core.shared.feedback_configuration as fbc
# import autograder.core.shared.utilities as ut

import autograder.utilities.fields as ag_fields
from autograder.core.models.utils import (
    PolymorphicModelValidatableOnSave, PolymorphicManagerWithValidateOnCreate)


# TODO: points configuration

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

        student_test_case_filename_pattern -- A string file pattern used to
            identify files that contain student test cases for this suite.
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
            This field can be empty but may NOT be None.
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
            and implementation file. This includes source code dependencies,
            files that the program will read from/write to, etc.
            NOTE: This list should NOT include buggy or correct
            implementation filenames. Those will be added automatically as
            per the evaluation protocol.

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

        points_per_buggy_implementation_exposed -- The number of points
            awarded for each buggy implementation exposed.
            This value must be >= 0
            Default value: zero

        feedback_configuration -- Specifies how much information should be
            included in serialized evaluation results.
            Default value: default-initialized
                StudentTestSuiteFeedbackConfiguration object

    Fat interface fields:
        compiler -- The program that will be used to compile the test case
            executables.
            See autograder.shared.global_constants.SUPPORTED_COMPILERS
            for a list of allowed values for this field.
            Default value: g++

        compiler_flags -- A list of option flags to be passed to the compiler.
            These flags are limited to the character set specified by
            autograder.shared.global_constants.COMMAND_LINE_ARG_WHITELIST_REGEX
            NOTE: This list should NOT include the names of files that
                need to be compiled and should not include flags that affect
                the name of the resulting executable program.
            This field is allowed to be empty.
            This field may not be None.
            Default value: empty list

        suite_resource_files_to_compile_together -- A list of filenames
            that will be compiled together with
            each student test case, implementation file pair.
            These filenames must be contained in suite_resource_filenames.
            This field is allowed to be empty.
            This field may not be None.
            Default value: empty list

        compile_implementation_files -- When this flag is True, the current
            correct of buggy implementation file will be compiled together
            with the current test case and specified resource files.
            When this value is False, the implementation files are NOT
            compiled together.
            Note that this field is only considered by types of test suite
            that use a compiler.
            Default value: True

        TODO
        interpreter --
        interpreter_flags --

    Abstract methods:
        evaluate()
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

    points_per_buggy_implementation_exposed = models.IntegerField(
        default=0, validators=[MinValueValidator(0)])

    feedback_configuration = ag_fields.JsonSerializableClassField(
        fbc.StudentTestSuiteFeedbackConfiguration,
        default=fbc.StudentTestSuiteFeedbackConfiguration
    )

    # -------------------------------------------------------------------------

    compiler = models.CharField(
        max_length=gc.MAX_CHAR_FIELD_LEN, default='g++',
        choices=zip(gc.SUPPORTED_COMPILERS, gc.SUPPORTED_COMPILERS))

    compiler_flags = ag_fields.StringArrayField(
        default=list, blank=True, string_validators=[
            RegexValidator(gc.COMMAND_LINE_ARG_WHITELIST_REGEX)])

    suite_resource_files_to_compile_together = ag_fields.StringArrayField(
        default=list, blank=True)

    compile_implementation_files = models.BooleanField(default=True)

    # -------------------------------------------------------------------------
    # -------------------------------------------------------------------------

    def evaluate(self, submission, autograder_sandbox):
        """
        Evaluates this student test suite and returns a StudentTestSuiteResult
        object that is linked to the given submission. The test suite
        will be evaluated inside the given AutograderSandbox.

        TODO: make the submission argument required for AutograderTestCaseBase.run()
            (alternitavely, have it copy the files if it's None or assume they exist
                in the sandbox otherwise, or vice-versa)
        NOTE: Unlike the run() method for AutograderTestCaseBase, the
            submission argument to this function may NOT be None.

        NOTE: This method does NOT save the result object to the database.

        This method must be overridden by derived classes.
        """
        raise NotImplementedError("Derived classes must override this method.")

    def clean(self):
        super().clean()

        errors = {}

        if self.name:
            self.name = self.name.strip()

        if not self.name:
            errors['name'] = "This field can't be empty"

        patterns = [pattern_obj.pattern for pattern_obj in
                    self.project.expected_student_file_patterns]

        if self.student_test_case_filename_pattern not in patterns:
            errors['student_test_case_filename_pattern'] = (
                'Pattern {} is not an expected student '
                'file pattern for project {}'.format(
                    self.student_test_case_filename_pattern,
                    self.project.name))

        errors.update(self._clean_suite_resource_files())

        if (self.correct_implementation_filename not in
                self.project.get_project_file_basenames()):
            errors['correct_implementation_filename'] = (
                '{} is not a resource file for project {}'.format(
                    self.correct_implementation_filename,
                    self.project.name))

        errors.update(self._clean_suite_resource_files_to_compile_together())
        errors.update(self._clean_buggy_implementation_filenames())

        if errors:
            raise ValidationError(errors)

    def _clean_suite_resource_files(self):
        project_filenames = self.project.get_project_file_basenames()
        errors = []

        for filename in self.suite_resource_filenames:
            if filename in project_filenames:
                continue

            errors.append(
                '{} is not a resource file for project {}'.format(
                    filename, self.project.name))

        if errors:
            return {'suite_resource_filenames': errors}

        return {}

    def _clean_suite_resource_files_to_compile_together(self):
        errors = []

        for filename in self.suite_resource_files_to_compile_together:
            if filename in self.suite_resource_filenames:
                continue

            errors.append(
                '{} is not a suite resource file for test suite {}'.format(
                    filename, self.name))

        if errors:
            return {'suite_resource_files_to_compile_together': errors}

        return {}

    def _clean_buggy_implementation_filenames(self):
        project_filenames = self.project.get_project_file_basenames()
        errors = []

        for filename in self.buggy_implementation_filenames:
            if filename in project_filenames:
                continue

            errors.append(
                '{} is not a resource file for project {}'.format(
                    filename, self.project.name))

        if errors:
            return {'buggy_implementation_filenames': errors}

        return {}
