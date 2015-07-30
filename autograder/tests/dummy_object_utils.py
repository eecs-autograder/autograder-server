import uuid
import base64

from django.contrib.auth.models import User

from autograder.models import Course, Semester, Project


def _get_unique_id():
    user_id = base64.b64encode(uuid.uuid4().bytes)
    # print(len(user_id))
    return user_id.decode('utf-8')


def create_dummy_users(num_users=1):
    """
    Returns a list containing the specified number of dummy users.
    If num_users is 1, the dummy user is returned on its own
    rather than as a list.
    """
    users = []

    for i in range(num_users):
        user_id = _get_unique_id()
        user = User.objects.create_user(
            first_name='fn{}'.format(user_id),
            last_name='ln{}'.format(user_id),
            username='usr{}'.format(user_id),
            email='jameslp@umich.edu',
            password='pw{}'.format(user_id))
        if num_users == 1:
            return user
        users.append(user)
    return users


def create_dummy_courses(num_courses=1):
    """
    Returns a list containing the specified number of dummy courses.
    If num_courses is 1, the dummy course is returned on its own
    rather than as a list.
    """
    courses = []
    for i in range(num_courses):
        user_id = _get_unique_id()
        course = Course.objects.validate_and_create(
            name='course{}'.format(user_id))
        if num_courses == 1:
            return course
        courses.append(course)
    return courses


def create_dummy_semesters(course, num_semesters=1):
    """
    Returns a list containing the specified number of dummy semesters.
    If num_semesters is 1, the dummy semester is returned on its own
    rather than as a list.
    """
    semesters = []
    for i in range(num_semesters):
        user_id = _get_unique_id()
        semester = Semester.objects.validate_and_create(
            name='semester{}'.format(user_id), course=course)
        if num_semesters == 1:
            return semester
        semesters.append(semester)
    return semesters


def create_dummy_projects(semester, num_projects=1):
    """
    Returns a list containing the specified number of dummy projects.
    If num_projects is 1, the dummy project is returned on its own
    rather than as a list.
    """
    projects = []
    for i in range(num_projects):
        user_id = _get_unique_id()
        project = Project.objects.validate_and_create(
            name='project{}'.format(user_id), semester=semester)
        if num_projects == 1:
            return project
        projects.append(project)
    return projects
