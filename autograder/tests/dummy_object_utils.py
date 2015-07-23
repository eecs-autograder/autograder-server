from django.contrib.auth.models import User

from autograder.models import Course, Semester, Project


def create_dummy_users(num_users=1):
    """
    Returns a list containing the specified number of dummy users.
    If num_users is 1, the dummy user is returned on its own
    rather than as a list.
    """
    users = []

    for i in range(num_users):
        user = User.objects.create_user(
            first_name='firstname{}'.format(i),
            last_name='lastname{}'.format(i),
            username='user{}'.format(i),
            email='jameslp@umich.edu',
            password='password{}'.format(i))
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
        course = Course.objects.validate_and_create(name='course{}'.format(i))
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
        semester = Semester.objects.validate_and_create(
            name='semester{}'.format(i), course=course)
        if num_semesters == 1:
            return semester
        semester.append(semester)
    return semesters


def create_dummy_projects(semester, num_projects=1):
    """
    Returns a list containing the specified number of dummy projects.
    If num_projects is 1, the dummy project is returned on its own
    rather than as a list.
    """
    projects = []
    for i in range(num_projects):
        project = Project.objects.validate_and_create(
            name='project{}'.format(i), semester=semester)
        if num_projects == 1:
            return project
        projects.append(project)
    return projects
