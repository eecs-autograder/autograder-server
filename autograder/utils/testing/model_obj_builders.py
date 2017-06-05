import copy
import random
import uuid
import base64
import typing

from django.contrib.auth.models import User
from django.core.files.uploadedfile import SimpleUploadedFile
from django.utils import timezone

import autograder.core.models as ag_models
from autograder.core.models.autograder_test_case.feedback_config import (
    FeedbackConfig, AGTestNameFdbkLevel, ReturnCodeFdbkLevel,
    StdoutFdbkLevel, StderrFdbkLevel, CompilationFdbkLevel,
    ValgrindFdbkLevel, PointsFdbkLevel)


def get_unique_id() -> str:
    """
    Returns a base64 encoded uuid as a string. The value returned can
    be added to a database object's fields to make them unique.
    A base64 representation is used because it is short enough to fit
    within the length restrictions of the "username" field of django
    User objects.
    """
    return base64.urlsafe_b64encode(uuid.uuid4().bytes).decode('utf-8')


def create_dummy_user(is_superuser: bool=False):
    """
    Creates a User with a random username. If is_superuser is True,
    creates the User with superuser status.
    """
    return create_dummy_users(1, is_superuser=is_superuser)[0]


def create_dummy_users(num_users: int, is_superuser: bool=False):
    """
    Creates list of num_users Users with random usernames.
    If is_superuser is True, creates each User with superuser status.
    """
    users = []

    for i in range(num_users):
        user_id = get_unique_id()
        user = User.objects.create_user(
            first_name='fn{}'.format(user_id),
            last_name='ln{}'.format(user_id),
            username='usr{}'.format(user_id),
            email='jameslp@umich.edu',
            password='pw{}'.format(user_id),
            is_superuser=is_superuser)
        users.append(user)
    return users


def build_course(course_kwargs: dict=None) -> ag_models.Course:
    """
    Creates a Course with a unique name.
    Any fields present in course_kwargs will be used instead of
    defaults.
    course_kwargs can also contain the following keys: admins, staff,
    and students. The values should be lists of Users, and those users
    will be added to the new course as admins, staff, or students,
    respectively.
    """
    if course_kwargs is None:
        course_kwargs = {}
    else:
        course_kwargs = copy.deepcopy(course_kwargs)

    if 'name' not in course_kwargs:
        course_kwargs['name'] = 'course{}'.format(get_unique_id())

    admins = course_kwargs.pop('administrators', [])
    staff = course_kwargs.pop('staff', [])
    students = course_kwargs.pop('enrolled_students', [])
    course = ag_models.Course.objects.validate_and_create(**course_kwargs)
    course.administrators.add(*admins)
    course.staff.add(*staff)
    course.enrolled_students.add(*students)

    return course


def make_admin_users(course: ag_models.Course, num_users: int) -> typing.Sequence[User]:
    users = create_dummy_users(num_users=num_users)
    course.administrators.add(*users)
    return users


def make_staff_users(course: ag_models.Course, num_users: int) -> typing.Sequence[User]:
    users = create_dummy_users(num_users=num_users)
    course.staff.add(*users)
    return users


def make_enrolled_users(course: ag_models.Course, num_users: int) -> typing.Sequence[User]:
    users = create_dummy_users(num_users=num_users)
    course.enrolled_students.add(*users)
    return users


def make_users(num_users: int) -> typing.Sequence[User]:
    return create_dummy_users(num_users=num_users)


def build_project(project_kwargs: dict=None, course_kwargs: dict=None) -> ag_models.Project:
    """
    Creates a Project with a unique name.
    Any fields in project_kwargs will be used instead of defaults.
    If the key "course" is present in project_kwargs, its value must
    be a Course that the new project will be linked to. The course will
    be initialized by calling build_course(course_kwargs).
    """
    if project_kwargs is None:
        project_kwargs = {}
    else:
        project_kwargs = copy.deepcopy(project_kwargs)

    if 'name' not in project_kwargs:
        project_kwargs['name'] = 'project{}'.format(get_unique_id())
    if 'course' not in project_kwargs:
        project_kwargs['course'] = build_course(course_kwargs=course_kwargs)

    project = ag_models.Project.objects.validate_and_create(**project_kwargs)
    return project


def build_compiled_ag_test(with_points=True,
                           **ag_test_kwargs) -> ag_models.CompiledAndRunAutograderTestCase:
    """
    Creates a CompiledAndRunAutograderTestCase object with a unique
    name.

    If with_points is True, then an arbitrary number of points will
    be assigned to each "points_" field on the object. Note that this
    includes an arbitrary deduction for valgrind errors.
    The total number of points to be awarded assuming all point
    allocations are awarded or deducted can be found in
    build_compiled_ag_test.points_with_all_used

    Any other keyword arguments specified will be set on the created
    object.
    If "project" is not specified as a keyword argument, then a
    Project will be created using build_project(), and the new object
    will be linked to that project.
    NOTE: If with_points is True, the following keyword arguments will
    be ignored:
        'points_for_correct_return_code'
        'expected_return_code'
        'points_for_correct_stdout'
        'expected_standard_output'
        'points_for_correct_stderr'
        'expected_standard_error_output'
        'deduction_for_valgrind_errors'
        'points_for_compilation_success'
        'use_valgrind'
    """
    if with_points:
        ag_test_kwargs.update({
            'points_for_correct_return_code': 3,
            'expected_return_code': 0,
            'points_for_correct_stdout': 2,
            'expected_standard_output': 'spam' * 1000,
            'points_for_correct_stderr': 4,
            'expected_standard_error_output': 'steve' * 1000,
            'deduction_for_valgrind_errors': 1,
            'points_for_compilation_success': 8,
            'use_valgrind': True
        })

    if 'name' not in ag_test_kwargs:
        ag_test_kwargs['name'] = 'ag_test_case{}'.format(get_unique_id())

    if 'project' not in ag_test_kwargs:
        ag_test_kwargs['project'] = build_project()

    if 'compiler' not in ag_test_kwargs:
        ag_test_kwargs['compiler'] = 'g++'
    if 'executable_name' not in ag_test_kwargs:
        ag_test_kwargs['executable_name'] = 'steve'

    return ag_models.AutograderTestCaseFactory.validate_and_create(
        'compiled_and_run_test_case', **ag_test_kwargs
    )
build_compiled_ag_test.points_with_all_used = 16  # type: ignore


def build_compiled_ag_test_result(ag_test_with_points=True,
                                  all_points_used=True,
                                  ag_test_kwargs=None,
                                  **result_kwargs) -> ag_models.AutograderTestCaseResult:
    """
    Creates an AutograderTestCaseResult object using the given data.
    If "test_case" is not passed as a keyword argument, then a new
    CompiledAndRunAutograderTestCase object will be created using
    build_compiled_ag_test(with_points=ag_test_with_points, **ag_test_kwargs)

    Similar to the other methods in this module, this function will try
    to use related objects passed through ag_test_kwargs or as keyword
    arguments, but will create new objects if none are passed.

    If all_points_used is True, then the result will be populated with
    data such that all the points for the associated
    CompiledAndRunAutograderTestCase object will be applied (including
    deductions). Specifically, the following fields will be overwritten:
        'return_code'
        'standard_output'
        'standard_error_output'
        'valgrind_return_code'
        'compilation_return_code'
    """
    if ag_test_kwargs is None:
        ag_test_kwargs = {}
    else:
        ag_test_kwargs = copy.deepcopy(ag_test_kwargs)

    submission = result_kwargs.get('submission', None)
    test_case = result_kwargs.get('test_case', None)
    project = ag_test_kwargs.get('project', None)
    if project is None:
        if test_case is not None:
            project = test_case.project
        else:
            project = build_project()
        ag_test_kwargs['project'] = project

    test_case_is_new = False
    if test_case is None:
        test_case = build_compiled_ag_test(
            with_points=ag_test_with_points, **ag_test_kwargs)
        result_kwargs['test_case'] = test_case
        test_case_is_new = True

    if submission is None:
        group = build_submission_group(group_kwargs={'project': project})
        submission = build_submission(submission_group=group)
        result_kwargs['submission'] = submission
    elif test_case_is_new:
        # If we were given an existing submission and created a new test
        # case, we need to create an empty result for the new test case.
        ag_models.AutograderTestCaseResult.objects.create(
            test_case=test_case, submission=submission)

    result_queryset = ag_models.AutograderTestCaseResult.objects.filter(
        test_case=test_case, submission=submission)
    if all_points_used:
        result_kwargs.update({
            'return_code': test_case.expected_return_code,
            'standard_output': test_case.expected_standard_output,
            'standard_error_output': test_case.expected_standard_error_output,
            'valgrind_return_code': 1,
            'compilation_return_code': 0
        })

    result_queryset.all().update(**result_kwargs)
    # This makes sure that the Python AutograderTestCaseBase object that
    # the result has a reference to is the same one that was passed in
    # to result_kwargs, if any.
    result = result_queryset.get()
    result.test_case = test_case
    return result


def build_submission_group(num_members=1,
                           group_kwargs=None,
                           project_kwargs=None,
                           course_kwargs=None) -> ag_models.SubmissionGroup:
    """
    Creates a SubmissionGroup with the specified data.
    If the "members" key is not present in group_kwargs, then
    num_members Users will be created and added to the group instead.
    """
    if group_kwargs is None:
        group_kwargs = {}
    else:
        group_kwargs = copy.deepcopy(group_kwargs)

    if 'project' not in group_kwargs:
        group_kwargs['project'] = build_project(
            project_kwargs=project_kwargs,
            course_kwargs=course_kwargs)

    project = group_kwargs['project']

    if 'members' not in group_kwargs:
        members = create_dummy_users(num_members)
        project.course.enrolled_students.add(*members)
        group_kwargs['members'] = members
    else:
        num_members = len(group_kwargs['members'])

    if num_members > project.max_group_size:
        project.validate_and_update(max_group_size=num_members)

    group = ag_models.SubmissionGroup.objects.validate_and_create(**group_kwargs)
    return group


def build_submission(**submission_kwargs) -> ag_models.Submission:
    """
    Creates a Submission with the given keyword arguments.
    If the "submission_group" argument is not specified, then a
    SubmissionGroup will be created with build_submission_group() and
    used instead.
    """
    group = submission_kwargs.pop('submission_group', build_submission_group())
    submitted_files = submission_kwargs.pop('submitted_files', [])
    timestamp = submission_kwargs.pop('timestamp', timezone.now())

    submission = ag_models.Submission.objects.validate_and_create(
        submission_group=group,
        submitted_files=submitted_files,
        timestamp=timestamp
    )
    for key, value in submission_kwargs.items():
        setattr(submission, key, value)

    submission.save()
    return submission


def build_submissions_with_results(num_submissions=1, num_tests=1,
                                   test_fdbk=None, make_one_best=False,
                                   **submission_kwargs):
    """
    Creates a list of Submissions, each with a set of results.
    All the submissions will be linked to the same SubmissionGroup. That
    group will either be specified as the "submission_group" keyword
    argument or created using "build_submission_group".

    The list will contain num_submissions submissions.
    num_tests CompiledAndRunAutograderTestCase objects will be created
    and added to the project that belongs to the SubmissionGroup being
    used. Therefore, you are advised to make sure that if you specify
    a SubmissionGroup and Project to use there are no test cases that
    belong to that Project.

    If make_one_best is True, then one of the Submissions besides the
    most recently created one will be modified so that it gets a
    higher score than all the other Submissions. In this case, this
    function returns a 3-tuple containing the list of submissions, the
    best submission, and the newly created test cases.

    Otherwise, returns a 2-tuple containing the list of submissions and
    the newly created test cases.
    """
    if num_submissions < 1:
        raise ValueError('num_submissions must be at least 1')

    if test_fdbk is None:
        test_fdbk = FeedbackConfig.create_with_max_fdbk()

    if 'submission_group' not in submission_kwargs:
        project = build_project()
        submission_kwargs['submission_group'] = build_submission_group(
            group_kwargs={'project': project})
    else:
        project = submission_kwargs['submission_group'].project

    tests = []
    for i in range(num_tests):
        fdbk = FeedbackConfig.objects.validate_and_create(**test_fdbk.to_dict())
        test = build_compiled_ag_test(
            with_points=True, project=project, feedback_configuration=fdbk)
        tests.append(test)

    submissions = []
    for i in range(num_submissions):
        submission = build_submission(**submission_kwargs)
        for test in tests:
            build_compiled_ag_test_result(test_case=test, submission=submission)

        submissions.append(submission)

    if make_one_best:
        if num_submissions < 2:
            raise Exception('In order to make a best submission, '
                            'num_submissions must be at least 2')
        # Choose a submission to be the best that is NOT the most recent
        best = random.choice(submissions[:-1])
        result_to_update = best.results.first()
        result_to_update.valgrind_return_code = 0
        result_to_update.save()

        expected_best_score = (
            build_compiled_ag_test.points_with_all_used * num_tests + 1)
        if best.basic_score != expected_best_score:
            raise Exception('Expected best score was incorrect: {}'.format(
                best.basic_score))

        return submissions, best, tests

    return submissions, tests


def random_fdbk() -> ag_models.FeedbackConfig:
    """
    Creates and returns a FeedbackConfig object with random (valid)
    values assigned to each of its fields.
    """
    fdbk = ag_models.FeedbackConfig.objects.validate_and_create(
        ag_test_name_fdbk=random.choice(
            [AGTestNameFdbkLevel.show_real_name,
             AGTestNameFdbkLevel.deterministically_obfuscate_name]),
        return_code_fdbk=random.choice(ReturnCodeFdbkLevel.values),
        stdout_fdbk=random.choice(StdoutFdbkLevel.values),
        stderr_fdbk=random.choice(StderrFdbkLevel.values),
        compilation_fdbk=random.choice(CompilationFdbkLevel.values),
        valgrind_fdbk=random.choice(ValgrindFdbkLevel.values),
        points_fdbk=random.choice(PointsFdbkLevel.values),
    )

    as_dict = fdbk.to_dict()
    norm_dict = ag_models.FeedbackConfig().to_dict()
    max_dict = ag_models.FeedbackConfig.create_with_max_fdbk().to_dict()
    ult_dict = (ag_models.FeedbackConfig
                         .create_ultimate_submission_default().to_dict())
    if as_dict == norm_dict or as_dict == max_dict or as_dict == ult_dict:
        return random_fdbk()

    return fdbk


def make_course(**kwargs):
    if 'name' not in kwargs:
        kwargs['name'] = 'course{}'.format(get_unique_id())

    return ag_models.Course.objects.validate_and_create(**kwargs)


def make_project(course: ag_models.Course=None, **project_kwargs) -> ag_models.Project:
    if course is None:
        course = make_course()

    if 'name' not in project_kwargs:
        project_kwargs['name'] = 'project{}'.format(get_unique_id())

    return ag_models.Project.objects.validate_and_create(course=course, **project_kwargs)


def make_uploaded_file(project: ag_models.Project) -> ag_models.UploadedFile:
    return ag_models.UploadedFile.objects.validate_and_create(
        file_obj=SimpleUploadedFile('file' + get_unique_id(), b'content'),
        project=project)


def make_group(num_members: int=1,
               members_role: ag_models.UserRole=ag_models.UserRole.student,
               project: ag_models.Project=None,
               **group_kwargs) -> ag_models.SubmissionGroup:
    if project is None:
        project = make_project()

    if 'members' not in group_kwargs:
        group_kwargs['members'] = create_dummy_users(num_members)

    if members_role == ag_models.UserRole.guest:
        project.validate_and_update(visible_to_guests=True)
    elif members_role == ag_models.UserRole.student:
        project.course.enrolled_students.add(*group_kwargs['members'])
    elif members_role == ag_models.UserRole.staff:
        project.course.staff.add(*group_kwargs['members'])
    elif members_role == ag_models.UserRole.admin:
        project.course.administrators.add(*group_kwargs['members'])

    return ag_models.SubmissionGroup.objects.validate_and_create(
        project=project, check_group_size_limits=False, **group_kwargs)


def make_ag_test_suite(project: ag_models.Project=None,
                       **ag_test_suite_args) -> ag_models.AGTestSuite:
    if project is None:
        project = make_project()

    if 'name' not in ag_test_suite_args:
        ag_test_suite_args['name'] = 'ag_test_suite{}'.format(get_unique_id())

    return ag_models.AGTestSuite.objects.validate_and_create(project=project, **ag_test_suite_args)


def make_ag_test_case(ag_test_suite: ag_models.AGTestSuite=None,
                      **ag_test_case_args) -> ag_models.AGTestCase:
    if ag_test_suite is None:
        ag_test_suite = make_ag_test_suite()

    if 'name' not in ag_test_case_args:
        ag_test_case_args['name'] = 'ag_test_case{}'.format(get_unique_id())

    return ag_models.AGTestCase.objects.validate_and_create(
        ag_test_suite=ag_test_suite, **ag_test_case_args)


def make_full_ag_test_command(
        ag_test_case: ag_models.AGTestCase=None,
        set_arbitrary_points=True,
        **ag_test_cmd_kwargs) -> ag_models.AGTestCommand:
    if ag_test_case is None:
        ag_test_case = make_ag_test_case()

    base_kwargs = {
        'name': 'ag_test_cmd-{}'.format(get_unique_id()),
        'ag_test_case': ag_test_case,
        'cmd': 'aksdjhfalsdf',

        # These specific values don't matter, other than that
        # they should indicate that return code, stdout, and
        # stderr are checked. We'll be manually setting the
        # correctness fields on AGTestCommandResults.
        'expected_return_code': ag_models.ExpectedReturnCode.zero,
        'expected_stdout_source': ag_models.ExpectedOutputSource.text,
        'expected_stdout_text': 'some text that is here because',
        'expected_stderr_source': ag_models.ExpectedOutputSource.text,
        'expected_stderr_text': 'some error stuff that wat',
    }

    if set_arbitrary_points:
        base_kwargs.update({
            'points_for_correct_return_code': 1,
            'points_for_correct_stdout': 2,
            'points_for_correct_stderr': 3,
            'deduction_for_wrong_return_code': -4,
            'deduction_for_wrong_stdout': -2,
            'deduction_for_wrong_stderr': -1
        })

    base_kwargs.update(ag_test_cmd_kwargs)
    return ag_models.AGTestCommand.objects.validate_and_create(**base_kwargs)


def make_correct_ag_test_command_result(ag_test_command: ag_models.AGTestCommand,
                                        ag_test_case_result: ag_models.AGTestCaseResult=None,
                                        submission: ag_models.Submission=None,
                                        **result_kwargs) -> ag_models.AGTestCommandResult:
    """
    Creates an AGTestCommandResult that is completely
    correct with respect to ag_test_command.
    If ag_test_case_result is None, an AGTestCaseResult
    and AGTestSuiteResult will be constructed that belong
    to submission. In this case, submission must not be
    None.
    """
    if ag_test_case_result is None:
        if submission is None:
            raise ValueError('submission must not be None when ag_test_case_result is None.')

        ag_test_suite_result = ag_models.AGTestSuiteResult.objects.validate_and_create(
            submission=submission, ag_test_suite=ag_test_command.ag_test_case.ag_test_suite)
        ag_test_case_result = ag_models.AGTestCaseResult.objects.validate_and_create(
            ag_test_suite_result=ag_test_suite_result, ag_test_case=ag_test_command.ag_test_case)

    return_code = (
        0 if ag_test_command.expected_return_code == ag_models.ExpectedReturnCode.zero else 42)

    stdout = ''
    if ag_test_command.expected_stdout_source == ag_models.ExpectedOutputSource.text:
        stdout = ag_test_command.expected_stdout_text
    elif ag_test_command.expected_stdout_source == ag_models.ExpectedOutputSource.project_file:
        with ag_test_command.expected_stdout_project_file.open() as f:
            stdout = f.read()

    stderr = ''
    if ag_test_command.expected_stderr_source == ag_models.ExpectedOutputSource.text:
        stderr = ag_test_command.expected_stderr_text
    elif ag_test_command.expected_stderr_source == ag_models.ExpectedOutputSource.project_file:
        with ag_test_command.expected_stderr_project_file.open() as f:
            stderr = f.read()

    kwargs = {
        'ag_test_command': ag_test_command,
        'ag_test_case_result': ag_test_case_result,
        'return_code': return_code,
        'stdout': stdout,
        'stderr': stderr,

        'return_code_correct': True,
        'stdout_correct': True,
        'stderr_correct': True,
    }

    kwargs.update(result_kwargs)

    return ag_models.AGTestCommandResult.objects.validate_and_create(**kwargs)


def make_incorrect_ag_test_command_result(ag_test_command: ag_models.AGTestCommand,
                                          ag_test_case_result: ag_models.AGTestCaseResult=None,
                                          submission: ag_models.Submission=None,
                                          **result_kwargs) -> ag_models.AGTestCommandResult:
    """
    Creates an AGTestCommandResult that is completely
    incorrect with respect to ag_test_command.
    If ag_test_case_result is None, an AGTestCaseResult
    and AGTestSuiteResult will be constructed that belong
    to submission. In this case, submission must not be
    None.
    """
    result = make_correct_ag_test_command_result(
        ag_test_command, ag_test_case_result, submission, **result_kwargs)
    result.return_code = 42 if result.return_code == 0 else 0
    result.stdout += 'laksdjhnflkajhdflkas'
    result.stderr += 'ncbsljksdkfjas'
    result.return_code_correct = False
    result.stdout_correct = False
    result.stderr_correct = False
    result.save()
    return result
