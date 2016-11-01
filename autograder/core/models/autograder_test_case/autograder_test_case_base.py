import fnmatch
import os
import itertools
import uuid

from django.core.cache import cache
from django.core.validators import (
    MinValueValidator, MaxValueValidator, RegexValidator)
from django.db import models, transaction

from ..ag_model_base import (
    PolymorphicAutograderModel, PolymorphicAutograderModelManager)
from ..project import Project, UploadedFile, ExpectedStudentFilePattern
from .feedback_config import FeedbackConfig

import autograder.core.constants as const
import autograder.core.utils as core_ut
import autograder.core.fields as ag_fields


def get_random_executable_name():
    return 'prog-{}'.format(uuid.uuid4().hex)


class AutograderTestCaseBase(PolymorphicAutograderModel):
    """
    This base class provides a fat interface for
    test cases used to evaluate student-submitted code.
    """
    class Meta:
        unique_together = ('name', 'project')

    objects = PolymorphicAutograderModelManager()

    _DEFAULT_TO_DICT_FIELDS = frozenset([
        'type_str',

        'name',
        'project',

        'deferred',

        'command_line_arguments',
        'standard_input',

        'time_limit',
        'allow_network_connections',
        'stack_size_limit',
        'virtual_memory_limit',
        'process_spawn_limit',

        'expected_return_code',
        'expect_any_nonzero_return_code',
        'expected_standard_output',
        'expected_standard_error_output',

        'use_valgrind',
        'valgrind_flags',

        'points_for_correct_return_code',
        'points_for_correct_stdout',
        'points_for_correct_stderr',
        'deduction_for_valgrind_errors',

        'feedback_configuration',
        'visible_to_students',

        'ultimate_submission_fdbk_conf',
        'visible_in_ultimate_submission',

        'past_submission_limit_fdbk_conf',
        'visible_in_past_limit_submission',

        'staff_viewer_fdbk_conf',

        'test_resource_files',
        'student_resource_files',

        'compiler',
        'compiler_flags',
        'executable_name',
        'points_for_compilation_success',

        'project_files_to_compile_together',
        'student_files_to_compile_together',

        'interpreter',
        'interpreter_flags',
        'entry_point_filename',
    ])

    @classmethod
    def get_default_to_dict_fields(class_):
        return class_._DEFAULT_TO_DICT_FIELDS

    _EDITABLE_FIELDS = frozenset([
        'name',

        'deferred',

        'command_line_arguments',
        'standard_input',

        'time_limit',
        'allow_network_connections',
        'stack_size_limit',
        'virtual_memory_limit',
        'process_spawn_limit',

        'expected_return_code',
        'expect_any_nonzero_return_code',
        'expected_standard_output',
        'expected_standard_error_output',

        'use_valgrind',
        'valgrind_flags',

        'points_for_correct_return_code',
        'points_for_correct_stdout',
        'points_for_correct_stderr',
        'deduction_for_valgrind_errors',

        'feedback_configuration',
        'visible_to_students',

        'ultimate_submission_fdbk_conf',
        'visible_in_ultimate_submission',

        'past_submission_limit_fdbk_conf',
        'visible_in_past_limit_submission',

        'staff_viewer_fdbk_conf',

        'test_resource_files',
        'student_resource_files',

        'points_for_compilation_success',
        'compiler',
        'compiler_flags',
        'executable_name',

        'project_files_to_compile_together',
        'student_files_to_compile_together',

        'interpreter',
        'interpreter_flags',
        'entry_point_filename',
    ])

    @classmethod
    def get_editable_fields(class_):
        return class_._EDITABLE_FIELDS

    # BASE FIELDS

    name = ag_fields.ShortStringField(
        help_text='''The name used to identify this test case.
            Must be non-empty and non-null. Must be unique among test
            cases associated with a given project.
            This field is REQUIRED.''')
    project = models.ForeignKey(
        Project,
        related_name='autograder_test_cases',
        help_text='''The Project this test case is associated with.
            This field is REQUIRED.''')

    deferred = models.BooleanField(
        default=False, blank=True,
        help_text='''A value of True indicates that this test case can
            be graded asynchronously and that submissions can be marked
            as finished grading before this test case finishes.''')

    command_line_arguments = ag_fields.StringArrayField(
        strip_strings=True, allow_empty_strings=False,
        default=list, blank=True,
        help_text='''A list of arguments to be passed to the program
            being tested.
            This list is allowed to be empty.
            This value may NOT be None.

            Individual arguments may contain alphanumeric characters,
            hyphen, underscore, period, and the equals sign.

            When ValidationError is raised for this field, the error
            message will be a list containing strings corresponding (in
            order) to each argument in this field. The strings will
            contain an error message for their corresponding argument or
            be empty if their corresponding argument did not cause an
            error.''')

    standard_input = models.TextField(
        blank=True,
        help_text='''A string whose contents
            should be sent to the standard input stream of the program
            being tested.''')

    test_resource_files = models.ManyToManyField(
        UploadedFile,
        related_name='ag_tests_required_by',
        help_text='''Uploaded project files that need to be
            in the same directory as the program being tested i.e.
            files that the program will read from/write to, etc.
            This list is allowed to be empty.
            This value may NOT be None.''')
    student_resource_files = models.ManyToManyField(
        ExpectedStudentFilePattern,
        related_name='ag_tests_required_by',
        help_text='''Student files that need to be
            in the same directory when the test case is run, i.e. source
            code files, etc.
            This list is allowed to be empty.
            This value may NOT be None.''')

    time_limit = models.IntegerField(
        default=const.DEFAULT_SUBPROCESS_TIMEOUT,
        validators=[MinValueValidator(1),
                    MaxValueValidator(const.MAX_SUBPROCESS_TIMEOUT)],
        help_text='''The time limit in seconds to be placed on the
            program being tested. This limit currently applies to each
            of: compilation, running the program, and running the
            program with Valgrind (the timeout is applied separately to
            each).
            Must be > 0
            Must be <= autograder.shared.global_constants
                                 .MAX_SUBPROCESS_TIMEOUT''')

    allow_network_connections = models.BooleanField(
        default=False,
        help_text='''Whether to allow the program being tested to make
            network connections.''')

    stack_size_limit = models.IntegerField(
        default=const.DEFAULT_STACK_SIZE_LIMIT,
        validators=[MinValueValidator(1),
                    MaxValueValidator(const.MAX_STACK_SIZE_LIMIT)],
        help_text='''
        stack_size_limit -- The maximum stack size in bytes.
            Must be > 0
            Must be <= autograder.shared.global_constants.MAX_STACK_SIZE_LIMIT
            NOTE: Setting this value too low may cause the program being
                    tested to crash prematurely.''')
    virtual_memory_limit = models.IntegerField(
        default=const.DEFAULT_VIRTUAL_MEM_LIMIT,
        validators=[MinValueValidator(1),
                    MaxValueValidator(const.MAX_VIRTUAL_MEM_LIMIT)],
        help_text='''The maximum amount of virtual memory
            (in bytes) the program being tested can use.
            Must be > 0
            Must be <= autograder.shared.global_constants.MAX_VIRTUAL_MEM_LIMIT
            NOTE: Setting this value too low may cause the program being
                    tested to crash prematurely.''')
    process_spawn_limit = models.IntegerField(
        default=const.DEFAULT_PROCESS_LIMIT,
        validators=[MinValueValidator(0),
                    MaxValueValidator(const.MAX_PROCESS_LIMIT)],
        help_text='''The maximum number of processes that the program
            being tested is allowed to spawn.
            Must be >= 0
            Must be <= autograder.shared.global_constants.MAX_PROCESS_LIMIT
            NOTE: This limit applies cumulatively to the processes
                    spawned by the main program being run. i.e. If a
                    spawned process spawns it's own child process, both
                    of those processes will count towards the main
                    program's process limit.''')

    expected_return_code = models.IntegerField(
        null=True, default=None, blank=True,
        help_text='''The return code that the program being tested
            should exit with in order to pass this test case.
            When expect_any_nonzero_return_code is False, a value of
                None indicates that this test case should not check the
                program's return code.''')
    expect_any_nonzero_return_code = models.BooleanField(
        default=False,
        help_text='''Indicates that rather than checking for a specific
            return code, this test case should evaluate whether the
            program being tested exited with any return code other than
            zero. If this field is True, the value of
            expected_return_code is ignored''')

    expected_standard_output = models.TextField(
        blank=True,
        help_text='''A string whose contents should be compared to the
            standard output of the program being tested. A value of the
            empty string indicates that this test case should not check
            the standard output of the program being tested.''')

    expected_standard_error_output = models.TextField(
        blank=True,
        help_text='''A string whose contents should be compared to the
            standard error output of the program being tested. A value
            of the empty string indicates that this test case should not
            check the standard error output of the program being
            tested.''')

    use_valgrind = models.BooleanField(
        default=False,
        help_text='''Whether this test case should perform a second
            run of the program being tested using the program Valgrind:
            http://valgrind.org/''')

    valgrind_flags = ag_fields.StringArrayField(
        null=True,
        strip_strings=True, allow_empty_strings=False,
        default=const.DEFAULT_VALGRIND_FLAGS, blank=True,
        help_text='''If use_valgrind is True, this field should contain
            a list of command line arguments to be passed to the
            valgrind program.
            NOTE: This list should NOT contain any
            details about the program being tested.
            Example value:
            ['--leak-check=full', '--error-exitcode=42'] This list can
            be empty. This list can only be None if use_valgrind is
            False.

            Default value: ['--leak-check=full', '--error-exitcode=1']
                if use_valgrind is true, None if use_valgrind is False.

            When ValidationError is raised for this field, the error
            message will be a list containing strings corresponding (in
            order) to each flag in this field. The strings will contain
            an error message for their corresponding flag or be empty if
            their corresponding flag did not cause an error.''')

    # Point distribution fields
    points_for_correct_return_code = models.IntegerField(
        default=0,
        validators=[MinValueValidator(0)],
        help_text='''The number of points to be awarded for the program
            being tested exiting with the correct return_code.''')
    points_for_correct_stdout = models.IntegerField(
        default=0,
        validators=[MinValueValidator(0)],
        help_text='''The number of points to be awarded
            for the program being tested producing the correct output
            to the stdout stream.''')
    points_for_correct_stderr = models.IntegerField(
        default=0,
        validators=[MinValueValidator(0)],
        help_text='''The number of points to be awarded
            for the program being tested producing the correct output
            to the stderr stream.''')
    deduction_for_valgrind_errors = models.IntegerField(
        default=0,
        validators=[MinValueValidator(0)],
        help_text='''The number of points to be deducted if the program
            being tested triggers any valgrind errors. Valgrind errors
            are indicated by a nonzero return code. This value is
            subtracted from the sum of return code and output points,
            and the result will NOT go below 0.''')

    # FEEDBACK SETTINGS ------------------------------------------------

    feedback_configuration = models.OneToOneField(
        FeedbackConfig, related_name='ag_test', blank=True, null=True,
        help_text='''Specifies how much information should be included
            in serialized test case results in normal situations. If not
            specified, this field is set to a default-constructed
            FeedbackConfig object.''')
    visible_to_students = models.BooleanField(
        default=False, blank=True,
        help_text='''Indicates whether results for this test case should
            be shown to students under normal circumstances.''')

    ultimate_submission_fdbk_conf = models.OneToOneField(
        FeedbackConfig, related_name='+', blank=True, null=True,
        help_text='''The feedback configuration to be used when a result
            belongs to a group's ultimate submission. If not specified,
            this field is set to
            FeedbackConfig.create_ultimate_submission_default()''')
    visible_in_ultimate_submission = models.BooleanField(
        default=True, blank=True,
        help_text='''Indicates whether results for this test case should
            be shown to students when part of a group's ultimate
            submission.''')

    past_submission_limit_fdbk_conf = models.OneToOneField(
        FeedbackConfig, related_name='+', blank=True, null=True,
        help_text='''The feedback configuration to be used when a result
            belongs to a submission that is past the daily submission
            limit. If not specified, this field is set to a default
            initialized FeedbackConfig object.''')
    visible_in_past_limit_submission = models.BooleanField(
        default=False, blank=True,
        help_text='''Indicates whether results for this test case should
            be shown to students when part of a submission that is past
            the daily limit.''')

    staff_viewer_fdbk_conf = models.OneToOneField(
        FeedbackConfig, related_name='+', blank=True, null=True,
        help_text='''The feedback configuration to be used when a result
            belongs to a submission being viewed by an outside staff
            member. If not specified, this field is set to
            FeedbackConfig.create_with_max_fdbk().''')

    # COMPILED AUTOGRADER TEST CASE FIELDS -----------------------------

    compiler = ag_fields.ShortStringField(
        blank=True,
        choices=zip(const.SUPPORTED_COMPILERS, const.SUPPORTED_COMPILERS),
        help_text='''The program that will be used to compile the test
            case executable.''')

    compiler_flags = ag_fields.StringArrayField(
        default=list, blank=True,
        help_text='''A list of option flags to be passed to the
            compiler. These flags are limited to the same character set
            as the command_line_arguments field.
            NOTE: This list should NOT include the names of files that
                need to be compiled and should not include flags that
                affect the name of the resulting executable program.''')

    project_files_to_compile_together = models.ManyToManyField(
        UploadedFile,
        related_name='ag_tests_compiled_by',
        help_text='''Uploaded project files that will be included when
            compiling the program.
            NOTE: These files do NOT need to be included in the
            test_resource_files relationship.''')

    student_files_to_compile_together = models.ManyToManyField(
        ExpectedStudentFilePattern,
        related_name='ag_tests_compiled_by',
        help_text='''Student-submitted files that will be included when
            compiling the program.
            NOTE: These files do NOT need to be included in the
            student_resource_files relationship.''')

    executable_name = ag_fields.ShortStringField(
        blank=True,
        default=get_random_executable_name,
        validators=[core_ut.check_user_provided_filename],
        help_text='''The name of the executable program that should be
            produced by the compiler. This is the program that will be
            tested.''')

    points_for_compilation_success = models.IntegerField(
        default=0,
        validators=[MinValueValidator(0)],
        help_text='''The number of points to be awarded for the program
            being tested compiling successfully.''')

    # INTERPRETED TEST CASE FIELDS -------------------------------------

    interpreter = ag_fields.ShortStringField(
        blank=True,
        choices=zip(const.SUPPORTED_INTERPRETERS, const.SUPPORTED_INTERPRETERS),
        help_text='''The interpreter used to run the program.''')

    interpreter_flags = ag_fields.StringArrayField(
        blank=True, default=list,
        help_text='''A list of objtion flags to be passed to the
            interpreter. These flags are limited to the same character
            set as the command_line_argument_field.''')

    entry_point_filename = ag_fields.ShortStringField(
        blank=True,
        validators=[core_ut.check_user_provided_filename],
        help_text='''The name of a file that should be given to the
            interpreter as the program to be run, i.e. the main source
            module. It is up to the user to make sure that this file is
            either a project or student resource file for this test.''')

    # -------------------------------------------------------------------------
    # -------------------------------------------------------------------------

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if self.use_valgrind and self.valgrind_flags is None:
            self.valgrind_flags = const.DEFAULT_VALGRIND_FLAGS

    def save(self, *args, **kwargs):
        with transaction.atomic():
            if self.feedback_configuration is None:
                self.feedback_configuration = (
                    FeedbackConfig.objects.validate_and_create())

            if self.ultimate_submission_fdbk_conf is None:
                self.ultimate_submission_fdbk_conf = (
                    FeedbackConfig.create_ultimate_submission_default())

            if self.past_submission_limit_fdbk_conf is None:
                self.past_submission_limit_fdbk_conf = (
                    FeedbackConfig.objects.validate_and_create())

            if self.staff_viewer_fdbk_conf is None:
                self.staff_viewer_fdbk_conf = (
                    FeedbackConfig.create_with_max_fdbk())

            super().save(*args, **kwargs)

        cache.delete_many(self.dependent_cache_keys)

    @property
    def dependent_cache_keys(self):
        dependent_keys = set()
        for result in self.dependent_results.all():
            dependent_keys.add(result.basic_score_cache_key)
            dependent_keys.add(result.submission.basic_score_cache_key)

        return dependent_keys

    def to_dict(self, **kwargs):
        result = super().to_dict(**kwargs)
        for fdbk_field in AutograderTestCaseBase.FDBK_FIELD_NAMES:
            if fdbk_field in result:
                result[fdbk_field] = getattr(self, fdbk_field).to_dict()

        return result

    FDBK_FIELD_NAMES = [
        'feedback_configuration', 'ultimate_submission_fdbk_conf',
        'past_submission_limit_fdbk_conf', 'staff_viewer_fdbk_conf']

    RELATED_FILE_FIELD_NAMES = [
        'test_resource_files',
        'student_resource_files',

        'project_files_to_compile_together',
        'student_files_to_compile_together',
    ]

    # -------------------------------------------------------------------------

    def run(self, submission, autograder_sandbox):
        """
        Runs this autograder test case and returns an
        AutograderTestCaseResult object that is linked to the given
        submission. The test case will be run inside the given
        AutograderSandbox. Any needed files will be added to the sandbox
        by this method.

        NOTE: This method does NOT save the result object to the
            database.

        This method must be overridden by derived classes.
        """
        raise NotImplementedError("Derived classes must override this method.")

    def add_needed_files_to_sandbox(self, submission, autograder_sandbox):
        """
        Adds all the files needed to run this test case to the given
        sandbox. This method should be called by derived-class
        implementations of the run() method.
        """
        # Add uploaded resource files and uploaded files to compile
        project_files_iter = itertools.chain(
            self.test_resource_files.all(),
            self.project_files_to_compile_together.all())
        files_to_add = (file_.abspath for file_ in project_files_iter)

        autograder_sandbox.add_files(*files_to_add)

        # Add student resource files and student files to compile
        student_files_iter = itertools.chain(
            self.student_resource_files.all(),
            self.student_files_to_compile_together.all())
        files_to_add = []
        for student_file in student_files_iter:
            matching_files = fnmatch.filter(submission.submitted_filenames,
                                            student_file.pattern)
            files_to_add += [
                os.path.join(core_ut.get_submission_dir(submission), filename)
                for filename in matching_files]

        if files_to_add:
            autograder_sandbox.add_files(*files_to_add)

    def checks_compilation(self):
        return False

    @property
    def type_str(self):
        raise NotImplementedError('Subclasses must override this property')
