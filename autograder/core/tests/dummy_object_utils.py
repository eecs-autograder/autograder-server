import uuid
import base64

from django.contrib.auth.models import User

from autograder.core.models import Course, Semester, Project, SubmissionGroup


def _get_unique_id():
    user_id = base64.urlsafe_b64encode(uuid.uuid4().bytes)
    # print(len(user_id))
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
    course = build_course(course_kwargs=course_kwargs)

    if semester_kwargs is None:
        semester_kwargs = {}

    if 'name' not in semester_kwargs:
        semester_kwargs['name'] = 'semester{}'.format(_get_unique_id())
    if 'course' not in semester_kwargs:
        semester_kwargs['course'] = course

    staff = semester_kwargs.pop('staff', [])
    enrolled = semester_kwargs.pop('enrolled_students', [])
    semester = Semester.objects.validate_and_create(**semester_kwargs)

    semester.staff.add(*staff)
    semester.enrolled_students.add(*enrolled)

    # semester.validate_and_save()
    return semester


def build_project(project_kwargs=None, semester_kwargs=None,
                  course_kwargs=None):
    semester = build_semester(
        semester_kwargs=semester_kwargs, course_kwargs=course_kwargs)

    if project_kwargs is None:
        project_kwargs = {}

    if 'name' not in project_kwargs:
        project_kwargs['name'] = 'project{}'.format(_get_unique_id())
    if 'semester' not in project_kwargs:
        project_kwargs['semester'] = semester

    project = Project.objects.validate_and_create(**project_kwargs)
    return project  # , semester, course


def build_submission_group(num_members=1, group_kwargs=None, project_kwargs=None,
                           semester_kwargs=None, course_kwargs=None):
    if group_kwargs is None:
        group_kwargs = {}

    project = build_project(
        project_kwargs=project_kwargs, semester_kwargs=semester_kwargs,
        course_kwargs=course_kwargs)

    if 'project' not in group_kwargs:
        group_kwargs['project'] = project

    if 'members' not in group_kwargs:
        members = create_dummy_users(num_members)
        project.semester.enrolled_students.add(*members)
        group_kwargs['members'] = [user.username for user in members]

    project.max_group_size = num_members
    project.save()

    group = SubmissionGroup.objects.validate_and_create(**group_kwargs)
    return group

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
