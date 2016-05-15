import uuid
import base64

from django.contrib.auth.models import User

from autograder.core.models import Course, Semester, Project, SubmissionGroup


def _get_unique_id():
    user_id = base64.urlsafe_b64encode(uuid.uuid4().bytes)
    return user_id.decode('utf-8')


def create_dummy_user():
    return create_dummy_users(1)[0]


def create_dummy_users(num_users):
    users = []

    for i in range(num_users):
        user_id = _get_unique_id()
        user = User.objects.create_user(
            first_name='fn{}'.format(user_id),
            last_name='ln{}'.format(user_id),
            username='usr{}'.format(user_id),
            email='jameslp@umich.edu',
            password='pw{}'.format(user_id))
        users.append(user)
    return users


def build_course(course_kwargs=None):
    if course_kwargs is None:
        course_kwargs = {}

    if 'name' not in course_kwargs:
        course_kwargs['name'] = 'course{}'.format(_get_unique_id())

    admins = course_kwargs.pop('administrators', [])
    course = Course.objects.validate_and_create(**course_kwargs)
    course.administrators.add(*admins)

    return course


def build_semester(semester_kwargs=None, course_kwargs=None):
    if semester_kwargs is None:
        semester_kwargs = {}

    if 'name' not in semester_kwargs:
        semester_kwargs['name'] = 'semester{}'.format(_get_unique_id())
    if 'course' not in semester_kwargs:
        semester_kwargs['course'] = build_course(course_kwargs=course_kwargs)

    staff = semester_kwargs.pop('staff', [])
    enrolled = semester_kwargs.pop('enrolled_students', [])
    semester = Semester.objects.validate_and_create(**semester_kwargs)

    semester.staff.add(*staff)
    semester.enrolled_students.add(*enrolled)

    return semester


def build_project(project_kwargs=None, semester_kwargs=None,
                  course_kwargs=None):
    if project_kwargs is None:
        project_kwargs = {}

    if 'name' not in project_kwargs:
        project_kwargs['name'] = 'project{}'.format(_get_unique_id())
    if 'semester' not in project_kwargs:
        project_kwargs['semester'] = build_semester(
            semester_kwargs=semester_kwargs, course_kwargs=course_kwargs)

    project = Project.objects.validate_and_create(**project_kwargs)
    return project


def build_submission_group(num_members=1, group_kwargs=None, project_kwargs=None,
                           semester_kwargs=None, course_kwargs=None):
    if group_kwargs is None:
        group_kwargs = {}

    if 'project' not in group_kwargs:
        group_kwargs['project'] = build_project(
            project_kwargs=project_kwargs, semester_kwargs=semester_kwargs,
            course_kwargs=course_kwargs)

    project = group_kwargs['project']

    if 'members' not in group_kwargs:
        members = create_dummy_users(num_members)
        project.semester.enrolled_students.add(*members)
        group_kwargs['members'] = members
    else:
        num_members = len(group_kwargs['members'])

    if num_members > project.max_group_size:
        project.validate_and_update(max_group_size=num_members)

    group = SubmissionGroup.objects.validate_and_create(**group_kwargs)
    return group
