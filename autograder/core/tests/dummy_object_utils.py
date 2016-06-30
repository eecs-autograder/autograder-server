import uuid
import base64

from django.contrib.auth.models import User

import autograder.core.models as ag_models


def _get_unique_id():
    user_id = base64.urlsafe_b64encode(uuid.uuid4().bytes)
    return user_id.decode('utf-8')


def create_dummy_user(is_superuser=False):
    return create_dummy_users(1, is_superuser=is_superuser)[0]


def create_dummy_users(num_users, is_superuser=False):
    users = []

    for i in range(num_users):
        user_id = _get_unique_id()
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
        course_kwargs['name'] = 'course{}'.format(_get_unique_id())

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
        project_kwargs['name'] = 'project{}'.format(_get_unique_id())
    if 'course' not in project_kwargs:
        project_kwargs['course'] = build_course(course_kwargs=course_kwargs)

    project = ag_models.Project.objects.validate_and_create(**project_kwargs)
    return project


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
