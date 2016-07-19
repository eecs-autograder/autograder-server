import random
import uuid
import base64

from django.contrib.auth.models import User

import autograder.core.models as ag_models
from autograder.core.models.autograder_test_case import feedback_config


def get_unique_id():
    user_id = base64.urlsafe_b64encode(uuid.uuid4().bytes)
    return user_id.decode('utf-8')


def create_dummy_user(is_superuser=False):
    return create_dummy_users(1, is_superuser=is_superuser)[0]


def create_dummy_users(num_users, is_superuser=False):
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


def build_course(course_kwargs=None):
    if course_kwargs is None:
        course_kwargs = {}

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


def build_project(project_kwargs=None, course_kwargs=None):
    if project_kwargs is None:
        project_kwargs = {}

    if 'name' not in project_kwargs:
        project_kwargs['name'] = 'project{}'.format(get_unique_id())
    if 'course' not in project_kwargs:
        project_kwargs['course'] = build_course(course_kwargs=course_kwargs)

    project = ag_models.Project.objects.validate_and_create(**project_kwargs)
    return project


def build_compiled_ag_test(with_points=True, **ag_test_kwargs):
    if with_points:
        ag_test_kwargs.update({
            'points_for_correct_return_code': 1,
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
        ag_test_kwargs['name'] = 'ag_test{}'.format(get_unique_id())

    if 'project' not in ag_test_kwargs:
        ag_test_kwargs['project'] = build_project()

    if 'compiler' not in ag_test_kwargs:
        ag_test_kwargs['compiler'] = 'g++'
    if 'executable_name' not in ag_test_kwargs:
        ag_test_kwargs['executable_name'] = 'steve'

    return ag_models.AutograderTestCaseFactory.validate_and_create(
        'compiled_and_run_test_case', **ag_test_kwargs
    )
build_compiled_ag_test.points_with_all_used = 14


def build_compiled_ag_test_result(ag_test_with_points=True,
                                  all_points_used=True,
                                  **result_kwargs):
    if 'test_case' not in result_kwargs:
        result_kwargs['test_case'] = build_compiled_ag_test(
            with_points=ag_test_with_points)

    if 'submission' not in result_kwargs:
        result_kwargs['submission'] = build_submission()

    ag_test = result_kwargs['test_case']
    if all_points_used:
        result_kwargs.update({
            'return_code': ag_test.expected_return_code,
            'standard_output': ag_test.expected_standard_output,
            'standard_error_output': ag_test.expected_standard_error_output,
            'valgrind_return_code': 1,
            'compilation_return_code': 0
        })

    return ag_models.AutograderTestCaseResult.objects.create(**result_kwargs)


def build_submission_group(num_members=1,
                           group_kwargs=None,
                           project_kwargs=None,
                           course_kwargs=None):
    if group_kwargs is None:
        group_kwargs = {}

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


def build_submission(**submission_kwargs):
    if 'submission_group' not in submission_kwargs:
        submission_kwargs['submission_group'] = build_submission_group()

    if 'submitted_files' not in submission_kwargs:
        submission_kwargs['submitted_files'] = []

    return ag_models.Submission.objects.validate_and_create(
        **submission_kwargs)


def build_submissions_with_results(num_submissions=1, num_tests=1,
                                   test_fdbk=None, make_one_best=False,
                                   **submission_kwargs):
    if num_submissions < 1:
        raise ValueError('num_submissions must be at least 1')

    if test_fdbk is None:
        test_fdbk = feedback_config.FeedbackConfig.create_with_max_fdbk()

    project = build_project()
    tests = []
    for i in range(num_tests):
        fdbk = feedback_config.FeedbackConfig.objects.validate_and_create(
            **test_fdbk.to_dict())
        test = build_compiled_ag_test(
            with_points=True, project=project, feedback_configuration=fdbk)
        tests.append(test)

    if 'submission_group' not in submission_kwargs:
        submission_kwargs['submission_group'] = build_submission_group(
            group_kwargs={'project': project})

    submissions = []
    for i in range(num_submissions):
        submission = build_submission(**submission_kwargs)

        for test in tests:
            build_compiled_ag_test_result(test_case=test,
                                          submission=submission)

        submissions.append(submission)

    if make_one_best:
        if num_submissions < 2:
            raise Exception('In order to make a best submission, '
                            'num_submissions must be at least 2')
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
