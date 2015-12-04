import uuid
import base64

from django.contrib.auth.models import User

from autograder.models import Course, Semester, Project


def _get_unique_id():
    user_id = base64.urlsafe_b64encode(uuid.uuid4().bytes)
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
        id_ = _get_unique_id()
        course = Course.objects.validate_and_create(
            name='course{}'.format(id_))
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
        id_ = _get_unique_id()
        semester = Semester.objects.validate_and_create(
            name='semester{}'.format(id_), course=course)
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
        id_ = _get_unique_id()
        project = Project.objects.validate_and_create(
            name='project{}'.format(id_), semester=semester)
        if num_projects == 1:
            return project
        projects.append(project)
    return projects


def build_project(project_kwargs=None, semester_kwargs=None, course_kwargs=None):
    if project_kwargs is None:
        project_kwargs = {}
    if semester_kwargs is None:
        semester_kwargs = {}
    if course_kwargs is None:
        course_kwargs = {}

    if 'name' not in course_kwargs:
        course_kwargs['name'] = 'course{}'.format(_get_unique_id())
    course = Course.objects.validate_and_create(**course_kwargs)

    if 'name' not in semester_kwargs:
        semester_kwargs['name'] = 'semester{}'.format(_get_unique_id())
    if 'course' not in semester_kwargs:
        semester_kwargs['course'] = course
    semester = Semester.objects.validate_and_create(**semester_kwargs)

    if 'name' not in project_kwargs:
        project_kwargs['name'] = 'project{}'.format(_get_unique_id())
    if 'semester' not in project_kwargs:
        project_kwargs['semester'] = semester

    return Project.objects.validate_and_create(**project_kwargs)

# def create_dummy_compiled_autograder_tests(project, num_tests=1):
#     """
#     Returns a list containing the specified number of dummy
#     compiled autograder test cases.
#     If num_tests is 1, the test case is returned on its own rather
#     than as a list.
#     """
#     tests = []
#     for i in range(num_tests):
#         id_ = _get_unique_id()
#         test = CompiledAutograderTestCase.objects.validate_and_create(
#             name='test{}'.format(id_), project=project)
#         if num_tests == 1:
#             return test
#         tests.append(test)
#     return tests
