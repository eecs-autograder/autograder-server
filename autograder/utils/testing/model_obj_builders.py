import copy
import uuid

from django.contrib.auth.models import User
from django.core.files.uploadedfile import SimpleUploadedFile
from django.utils import timezone
from typing import Sequence, Optional

import autograder.core.models as ag_models
from autograder.core import utils as core_ut


def get_unique_id() -> str:
    """
    Returns a hex encoded uuid as a string. The value returned can
    be added to a database object's fields to make them unique.
    """
    return uuid.uuid4().hex


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
            first_name='steve',  # first_name length limit is 30 chars
            last_name='ln{}'.format(user_id),
            username='usr{}'.format(user_id),
            email='jameslp@umich.edu',
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

    admins = course_kwargs.pop('admins', [])
    staff = course_kwargs.pop('staff', [])
    students = course_kwargs.pop('students', [])
    course = ag_models.Course.objects.validate_and_create(**course_kwargs)
    course.admins.add(*admins)
    course.staff.add(*staff)
    course.students.add(*students)

    return course


def make_admin_users(course: ag_models.Course, num_users: int) -> Sequence[User]:
    users = create_dummy_users(num_users=num_users)
    course.admins.add(*users)
    return users


def make_admin_user(course: ag_models.Course) -> User:
    return make_admin_users(course, 1)[0]


def make_staff_users(course: ag_models.Course, num_users: int) -> Sequence[User]:
    users = create_dummy_users(num_users=num_users)
    course.staff.add(*users)
    return users


def make_staff_user(course: ag_models.Course) -> User:
    return make_staff_users(course, 1)[0]


def make_student_users(course: ag_models.Course, num_users: int) -> Sequence[User]:
    users = create_dummy_users(num_users=num_users)
    course.students.add(*users)
    return users


def make_student_user(course: ag_models.Course) -> User:
    return make_student_users(course, 1)[0]


def make_handgrader_users(course: ag_models.Course, num_users: int) -> Sequence[User]:
    users = create_dummy_users(num_users=num_users)
    course.handgraders.add(*users)
    return users


def make_handgrader_user(course: ag_models.Course) -> User:
    return make_handgrader_users(course, 1)[0]


def make_users(num_users: int, superuser=False) -> Sequence[User]:
    return create_dummy_users(num_users=num_users, is_superuser=superuser)


def make_user(superuser=False) -> User:
    """
    Creates a user a random username and no domain in that username.
    """
    return make_users(num_users=1, superuser=superuser)[0]


def make_allowed_domain_guest_user(course: ag_models.Course) -> User:
    user = make_user()
    user.username += course.allowed_guest_domain
    user.save()
    return user


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


def build_group(num_members=1,
                group_kwargs=None,
                project_kwargs=None,
                course_kwargs=None) -> ag_models.Group:
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
        project.course.students.add(*members)
        group_kwargs['members'] = members
    else:
        num_members = len(group_kwargs['members'])

    if num_members > project.max_group_size:
        project.validate_and_update(max_group_size=num_members)

    group = ag_models.Group.objects.validate_and_create(**group_kwargs)
    return group


def make_submission(group: Optional[ag_models.Group]=None,
                    **submission_kwargs) -> ag_models.Submission:
    """
    Creates a Submission with the given keyword arguments.
    If the "group" argument is None, then a
    SubmissionGroup will be created with make_group() and
    used instead.
    Any fields passed in as submission_kwargs will be set derectly on
    the submission after it is created in order to bypass the
    restricted set of fields that Submission.objects.validate_and_create
    accepts.
    """
    if group is None:
        group = make_group()
    submitted_files = submission_kwargs.pop('submitted_files', [])
    timestamp = submission_kwargs.pop('timestamp', timezone.now())

    submission = ag_models.Submission.objects.validate_and_create(
        group=group,
        submitted_files=submitted_files,
        timestamp=timestamp
    )
    for key, value in submission_kwargs.items():
        setattr(submission, key, value)

    submission.save()
    return submission


def make_finished_submission(group: Optional[ag_models.Group]=None,
                             **submission_kwargs) -> ag_models.Submission:
    return make_submission(status=ag_models.Submission.GradingStatus.finished_grading,
                           group=group,
                           **submission_kwargs)


def make_course(**kwargs) -> ag_models.Course:
    if 'name' not in kwargs:
        kwargs['name'] = 'course{}'.format(get_unique_id())

    return ag_models.Course.objects.validate_and_create(**kwargs)


def make_sandbox_docker_image(course: ag_models.Course=None) -> ag_models.SandboxDockerImage:
    return ag_models.SandboxDockerImage.objects.validate_and_create(
        course=course,
        display_name='Image ' + get_unique_id(),
        tag='tag' + get_unique_id()
    )


def make_project(course: ag_models.Course=None, **project_kwargs) -> ag_models.Project:
    if course is None:
        course = make_course()

    if 'name' not in project_kwargs:
        project_kwargs['name'] = 'project{}'.format(get_unique_id())

    return ag_models.Project.objects.validate_and_create(course=course, **project_kwargs)


def make_instructor_file(project: ag_models.Project) -> ag_models.InstructorFile:
    return ag_models.InstructorFile.objects.validate_and_create(
        file_obj=SimpleUploadedFile('file' + get_unique_id(), b'content'),
        project=project)


def make_expected_student_file(
    project: ag_models.Project,
    **kwargs
) -> ag_models.ExpectedStudentFile:
    if 'pattern' not in kwargs:
        kwargs['pattern'] = 'pattern' + get_unique_id()
    return ag_models.ExpectedStudentFile.objects.validate_and_create(project=project, **kwargs)


class UserRole(core_ut.OrderedEnum):
    guest = 'guest'
    student = 'student'
    handgrader = 'handgrader'
    staff = 'staff'
    admin = 'admin'


def make_group(num_members: int=1,
               members_role: UserRole=UserRole.student,
               project: ag_models.Project=None,
            #    members: Optional[Sequence[User]]=None,
               **group_kwargs) -> ag_models.Group:
    if project is None:
        project = make_project()

    # if members is None:
    members = make_users(num_members)

    if members_role == UserRole.guest:
        project.validate_and_update(guests_can_submit=True)
    elif members_role == UserRole.student:
        project.course.students.add(*members)
    elif members_role == UserRole.staff:
        project.course.staff.add(*members)
    elif members_role == UserRole.admin:
        project.course.admins.add(*members)

    return ag_models.Group.objects.validate_and_create(
        members=members,
        project=project,
        check_group_size_limits=False,
        **group_kwargs)


def make_group_invitation(
    # sender: User=None,
    # recipients: Sequence[User]=None,
    project: ag_models.Project=None,
    num_recipients: int=1,
    users_role: UserRole=UserRole.student,
):
    if project is None:
        project = make_project()

    # if sender is None:
    sender = make_user()

    # if recipients is None:
    recipients = make_users(num_recipients)

    project.max_group_size = 1 + len(recipients)
    project.save()

    if users_role == UserRole.guest:
        project.validate_and_update(guests_can_submit=True)
    elif users_role == UserRole.student:
        project.course.students.add(sender, *recipients)
    elif users_role == UserRole.staff:
        project.course.staff.add(sender, *recipients)
    elif users_role == UserRole.admin:
        project.course.admins.add(sender, *recipients)

    return ag_models.GroupInvitation.objects.validate_and_create(
        sender, recipients, project=project)


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
        set_arbitrary_expected_vals=True,
        **ag_test_cmd_kwargs) -> ag_models.AGTestCommand:
    if ag_test_case is None:
        ag_test_case = make_ag_test_case()

    base_kwargs = {
        'name': 'ag_test_cmd-{}'.format(get_unique_id()),
        'ag_test_case': ag_test_case,
        'cmd': 'printf ""',
    }

    if set_arbitrary_expected_vals:
        base_kwargs.update({
            # These specific values don't matter, other than that
            # they should indicate that return code, stdout, and
            # stderr are checked. We'll be manually setting the
            # correctness fields on AGTestCommandResults.
            'expected_return_code': ag_models.ExpectedReturnCode.zero,
            'expected_stdout_source': ag_models.ExpectedOutputSource.text,
            'expected_stdout_text': 'some text that is here because',
            'expected_stderr_source': ag_models.ExpectedOutputSource.text,
            'expected_stderr_text': 'some error stuff that wat',
        })

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
    elif ag_test_command.expected_stdout_source == ag_models.ExpectedOutputSource.instructor_file:
        with ag_test_command.expected_stdout_instructor_file.open() as f:
            stdout = f.read()

    stderr = ''
    if ag_test_command.expected_stderr_source == ag_models.ExpectedOutputSource.text:
        stderr = ag_test_command.expected_stderr_text
    elif ag_test_command.expected_stderr_source == ag_models.ExpectedOutputSource.instructor_file:
        with ag_test_command.expected_stderr_instructor_file.open() as f:
            stderr = f.read()

    kwargs = {
        'ag_test_command': ag_test_command,
        'ag_test_case_result': ag_test_case_result,
        'return_code': return_code,

        'return_code_correct': True,
        'stdout_correct': True,
        'stderr_correct': True,
    }

    kwargs.update(result_kwargs)

    result = ag_models.AGTestCommandResult.objects.validate_and_create(**kwargs)
    with open(result.stdout_filename, 'w') as f:
        f.write(stdout)

    with open(result.stderr_filename, 'w') as f:
        f.write(stderr)

    return result


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
    result.return_code_correct = False
    result.stdout_correct = False
    result.stderr_correct = False
    result.save()

    with open(result.stdout_filename, 'a') as f:
        f.write('laksdjhnflkajhdflkas')

    with open(result.stderr_filename, 'a') as f:
        f.write('ncbsljksdkfjas')

    return result


def make_student_test_suite(project: ag_models.Project=None,
                            **student_test_suite_kwargs) -> ag_models.StudentTestSuite:
    if project is None:
        project = make_project()

    if 'name' not in student_test_suite_kwargs:
        student_test_suite_kwargs['name'] = 'student_test_suite{}'.format(get_unique_id())

    return ag_models.StudentTestSuite.objects.validate_and_create(
        project=project, **student_test_suite_kwargs)
