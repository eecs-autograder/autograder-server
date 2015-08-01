import json

from django.contrib.auth.models import User
from django.test import RequestFactory
from django.core.urlresolvers import reverse, resolve
from django.core.exceptions import ObjectDoesNotExist

from autograder.tests.temporary_filesystem_test_case import (
    TemporaryFilesystemTestCase)

from autograder.frontend import ajax_request_handlers
from autograder.frontend.json_api_serializers import (
    course_to_json, semester_to_json, project_to_json)
from autograder.models import Semester, SubmissionGroup

import autograder.tests.dummy_object_utils as obj_ut


# print(json.dumps(expected, sort_keys=True, indent=4))
# print(json.dumps(actual, sort_keys=True, indent=4))


def _bytes_to_json(data):
    return json.loads(data.decode('utf-8'))


def _process_get_request(url, user):
    rf = RequestFactory()

    request = rf.get(url)
    request.user = user

    resolved = resolve(request.path)
    return resolved.func(request, *resolved.args, **resolved.kwargs)


def _process_patch_request(url, data, user):
    rf = RequestFactory()

    request = rf.patch(url, data)
    request.user = user

    resolved = resolve(request.path)
    return resolved.func(request, *resolved.args, **resolved.kwargs)


# -----------------------------------------------------------------------------
# -----------------------------------------------------------------------------

def _get_course_request(course_id, user):
    url = '/courses/course/{}/'.format(course_id)
    return _process_get_request(url, user)


def _list_courses_request(user):
    url = '/courses/'
    return _process_get_request(url, user)


def _get_semester_request(semester_id, user):
    url = '/semesters/semester/{}/'.format(semester_id)
    return _process_get_request(url, user)


def _list_semesters_request(user):
    url = '/semesters/'
    return _process_get_request(url, user)


def _patch_semester_request(semester_id, user,
                            staff_to_add=None, staff_to_remove=None,
                            students_to_add=None, students_to_remove=None):
    url = '/semesters/semester/{}/'.format(semester_id)
    data = {
        'data': {
            'type': 'semester',
            'id': semester_id
        },
        'meta': {
        }
    }

    if staff_to_add is not None:
        data['meta']['add_semester_staff'] = [
            user_obj.username for user_obj in staff_to_add
        ]

    if staff_to_remove is not None:
        data['meta']['remove_semester_staff'] = [
            user_obj.username for user_obj in staff_to_remove
        ]

    if students_to_add is not None:
        data['meta']['add_enrolled_students'] = [
            user_obj.username for user_obj in students_to_add
        ]

    if students_to_remove is not None:
        data['meta']['remove_enrolled_students'] = [
            user_obj.username for user_obj in students_to_remove
        ]

    return _process_patch_request(url, json.dumps(data), user)


# -----------------------------------------------------------------------------
# -----------------------------------------------------------------------------

class CourseRequestHandlerTestCase(TemporaryFilesystemTestCase):
    def setUp(self):
        super().setUp()

        self.maxDiff = None

        self.rf = RequestFactory()

        self.courses = obj_ut.create_dummy_courses(5)

    def test_get_course_as_admin(self):
        course_admin = obj_ut.create_dummy_users()
        course = self.courses[2]

        course.add_course_admins(course_admin)

        response = _get_course_request(course.pk, course_admin)

        self.assertEqual(200, response.status_code)

        content = _bytes_to_json(response.content)
        self.assertEqual(
            content,
            {
                'data': course_to_json(course),
                'included': []
            })

    def test_get_course_that_has_semesters(self):
        course_admin = obj_ut.create_dummy_users()
        course = self.courses[0]
        course.add_course_admins(course_admin)

        semesters = obj_ut.create_dummy_semesters(course, 9)

        response = _get_course_request(course.pk, course_admin)

        self.assertEqual(200, response.status_code)

        content = _bytes_to_json(response.content)
        self.assertEqual(
            content,
            {
                'data': course_to_json(course),
                'included': [
                    {
                        'data': semester_to_json(
                            semester, with_fields=False,
                            user_is_semester_staff=True)
                    }
                    for semester in semesters
                ]
            })

    def test_get_course_permission_denied(self):
        user = obj_ut.create_dummy_users()
        response = _get_course_request(self.courses[0].pk, user)

        self.assertEqual(403, response.status_code)

    def test_get_course_not_found(self):
        user = obj_ut.create_dummy_users()
        response = _get_course_request(42, user)

        self.assertEqual(404, response.status_code)

    def test_list_courses_course_admin(self):
        course_admin = obj_ut.create_dummy_users()

        subset = sorted(
            (self.courses[1], self.courses[4]), key=lambda obj: obj.name)
        self.courses[1].add_course_admins(course_admin)
        self.courses[4].add_course_admins(course_admin)

        expected = {
            'data': [
                course_to_json(course) for course in subset
            ]
        }

        response = _list_courses_request(course_admin)

        self.assertEqual(200, response.status_code)
        self.assertEqual(expected, _bytes_to_json(response.content))

    def test_list_courses_empty_list_non_admin(self):
        user = obj_ut.create_dummy_users()

        response = _list_courses_request(user)

        expected = {'data': []}

        self.assertEqual(200, response.status_code)
        self.assertEqual(expected, _bytes_to_json(response.content))

    # -------------------------------------------------------------------------

    # Move to Django Admin page

    # def test_add_course_success(self):
    #     self.fail()

    # def test_add_course_permission_denied(self):
    #     self.fail()


    # def test_add_course_admin_success(self):
    #     self.fail()

    # def test_add_course_admin_permission_denied(self):
    #     self.fail()


    # def test_remove_course_admin_success(self):
    #     self.fail()

    # def test_remove_course_admin_does_not_exist(self):
    #     self.fail()

    # def test_remove_course_admin_permission_denied(self):
    #     self.fail()

    # -------------------------------------------------------------------------


class GetSemesterRequestTestCase(TemporaryFilesystemTestCase):
    def setUp(self):
        super().setUp()

        self.user = obj_ut.create_dummy_users()

        self.course = obj_ut.create_dummy_courses()
        self.semester = obj_ut.create_dummy_semesters(self.course)

        self.visible_project = obj_ut.create_dummy_projects(self.semester)
        self.visible_project.visible_to_students = True
        self.visible_project.validate_and_save()

        self.hidden_project = obj_ut.create_dummy_projects(self.semester)

    def test_get_semester_as_course_admin(self):
        self.course.add_course_admins(self.user)

        response = _get_semester_request(self.semester.pk, self.user)
        self.assertEqual(200, response.status_code)

        sort_key = lambda obj: obj['id']
        expected = {
            'data': semester_to_json(
                self.semester, user_is_semester_staff=True),
            'included': sorted([
                project_to_json(self.visible_project, with_fields=False),
                project_to_json(self.hidden_project, with_fields=False)
            ], key=sort_key)
        }

        actual = _bytes_to_json(response.content)
        actual['included'] = sorted(actual['included'], key=sort_key)

        self.assertEqual(expected, actual)

    def test_get_semester_as_staff(self):
        self.semester.add_semester_staff(self.user)

        response = _get_semester_request(self.semester.pk, self.user)
        self.assertEqual(200, response.status_code)

        sort_key = lambda obj: obj['id']
        expected = {
            'data': semester_to_json(
                self.semester, user_is_semester_staff=True),
            'included': sorted([
                project_to_json(self.visible_project, with_fields=False),
                project_to_json(self.hidden_project, with_fields=False)
            ], key=sort_key)
        }

        actual = _bytes_to_json(response.content)
        actual['included'] = sorted(actual['included'], key=sort_key)

        self.assertEqual(expected, actual)

    def test_get_semester_as_enrolled_student(self):
        self.semester.add_enrolled_students(self.user)

        response = _get_semester_request(self.semester.pk, self.user)
        self.assertEqual(200, response.status_code)

        sort_key = lambda obj: obj['id']
        expected = {
            'data': semester_to_json(
                self.semester, user_is_semester_staff=False),
            'included': sorted([
                project_to_json(self.visible_project, with_fields=False)
            ], key=sort_key)
        }

        actual = _bytes_to_json(response.content)
        actual['included'] = sorted(actual['included'], key=sort_key)

        self.assertEqual(expected, actual)

    def test_get_semester_permission_denied(self):
        response = _get_semester_request(self.semester.pk, self.user)
        self.assertEqual(403, response.status_code)


# -----------------------------------------------------------------------------

class ListSemestersRequestTestCase(TemporaryFilesystemTestCase):
    def setUp(self):
        super().setUp()

        self.maxDiff = None

        self.user = obj_ut.create_dummy_users()

        self.course1 = obj_ut.create_dummy_courses()
        self.semesters1 = obj_ut.create_dummy_semesters(self.course1, 2)

        self.course2 = obj_ut.create_dummy_courses()
        self.semesters2 = obj_ut.create_dummy_semesters(self.course2, 3)

        self.semesters = self.semesters1 + self.semesters2

    def test_list_semesters_course_admin(self):
        self.course1.add_course_admins(self.user)
        self.course2.add_course_admins(self.user)

        response = _list_semesters_request(self.user)
        self.assertEqual(200, response.status_code)

        sort_key = lambda obj: obj['id']
        expected = {
            'data': sorted([
                semester_to_json(semester, user_is_semester_staff=True)
                for semester in self.semesters
            ], key=sort_key)
        }

        actual = _bytes_to_json(response.content)
        actual['data'] = sorted(actual['data'], key=sort_key)

        self.assertEqual(expected, actual)

    def test_list_semesters_staff_member(self):
        subset = [self.semesters1[1], self.semesters2[-1]]
        for semester in subset:
            semester.add_semester_staff(self.user)

        response = _list_semesters_request(self.user)
        self.assertEqual(200, response.status_code)

        sort_key = lambda obj: obj['id']
        expected = {
            'data': sorted([
                semester_to_json(semester, user_is_semester_staff=True)
                for semester in subset
            ], key=sort_key)
        }

        actual = _bytes_to_json(response.content)
        actual['data'] = sorted(actual['data'], key=sort_key)

        self.assertEqual(expected, actual)

    def test_list_semesters_enrolled_student(self):
        subset = [self.semesters1[0], self.semesters2[-2]]
        for semester in subset:
            semester.add_enrolled_students(self.user)

        response = _list_semesters_request(self.user)
        self.assertEqual(200, response.status_code)

        sort_key = lambda obj: obj['id']
        expected = {
            'data': sorted([
                semester_to_json(semester, user_is_semester_staff=False)
                for semester in subset
            ], key=sort_key)
        }

        actual = _bytes_to_json(response.content)
        actual['data'] = sorted(actual['data'], key=sort_key)

        self.assertEqual(expected, actual)

    def test_list_semesters_enrolled_student_and_semester_staff(self):
        self.semesters1[0].add_semester_staff(self.user)
        self.semesters2[-2].add_enrolled_students(self.user)

        expected = {
            'data': [
                semester_to_json(
                    self.semesters1[0], user_is_semester_staff=True),
                semester_to_json(
                    self.semesters2[-2], user_is_semester_staff=False)
            ]
        }

        response = _list_semesters_request(self.user)

        self.assertEqual(200, response.status_code)
        self.assertEqual(expected, _bytes_to_json(response.content))

    def test_list_semesters_nobody_user(self):
        response = _list_semesters_request(self.user)

        self.assertEqual(200, response.status_code)
        self.assertEqual({'data': []}, _bytes_to_json(response.content))


# -----------------------------------------------------------------------------

class PatchSemesterTestCase(TemporaryFilesystemTestCase):
    def setUp(self):
        super().setUp()

        self.admin = obj_ut.create_dummy_users()
        self.staff = obj_ut.create_dummy_users(5)
        self.students = obj_ut.create_dummy_users(4)

        self.course = obj_ut.create_dummy_courses()
        self.semester = obj_ut.create_dummy_semesters(self.course)
        self.semester.add_semester_staff(*self.staff)
        self.semester.add_enrolled_students(*self.students)

        self.course.add_course_admins(self.admin)

        self.enrolled = obj_ut.create_dummy_users()
        self.semester.add_enrolled_students(self.enrolled)

        self.nobody = obj_ut.create_dummy_users()

    def test_valid_add_staff_members(self):
        new_staff = obj_ut.create_dummy_users(2)
        for user in new_staff:
            self.assertFalse(self.semester.is_semester_staff(user))

        response = _patch_semester_request(
            self.semester.pk, self.admin, staff_to_add=new_staff)
        self.assertEqual(204, response.status_code)

        loaded = Semester.objects.get(pk=self.semester.pk)
        for user in new_staff:
            self.assertTrue(loaded.is_semester_staff(user))

    def test_valid_remove_staff_members(self):
        to_remove = [self.staff[1], self.staff[3]]
        for user in to_remove:
            self.assertTrue(self.semester.is_semester_staff(user))

        response = _patch_semester_request(
            self.semester.pk, self.admin, staff_to_remove=to_remove)
        self.assertEqual(204, response.status_code)

        loaded = Semester.objects.get(pk=self.semester.pk)
        for user in to_remove:
            self.assertFalse(loaded.is_semester_staff(user))

    def test_add_staff_members_permission_denied(self):
        new_staff = obj_ut.create_dummy_users(2)
        # Staff member (non-admin)
        response = _patch_semester_request(
            self.semester.pk, self.staff[0], staff_to_add=new_staff)
        self.assertEqual(403, response.status_code)

        # enrolled student
        response = _patch_semester_request(
            self.semester.pk, self.enrolled, staff_to_add=new_staff)
        self.assertEqual(403, response.status_code)

        # nobody user
        response = _patch_semester_request(
            self.semester.pk, self.nobody, staff_to_add=new_staff)
        self.assertEqual(403, response.status_code)

    def test_remove_staff_members_permission_denied(self):
        to_remove = [self.staff[1], self.staff[3]]

        # Staff member (non-admin)
        response = _patch_semester_request(
            self.semester.pk, self.staff[0], staff_to_remove=to_remove)
        self.assertEqual(403, response.status_code)

        # enrolled student
        response = _patch_semester_request(
            self.semester.pk, self.enrolled, staff_to_remove=to_remove)
        self.assertEqual(403, response.status_code)

        # nobody user
        response = _patch_semester_request(
            self.semester.pk, self.nobody, staff_to_remove=to_remove)
        self.assertEqual(403, response.status_code)

    def test_invalid_request_add_and_remove_staff_members(self):
        new_users = obj_ut.create_dummy_users(2)
        to_remove = [self.staff[1], self.staff[3]]

        response = _patch_semester_request(
            self.semester.pk, self.admin,
            staff_to_remove=to_remove, staff_to_add=new_users)
        self.assertEqual(400, response.status_code)

    # -------------------------------------------------------------------------

    def test_valid_add_students(self):
        new_students = obj_ut.create_dummy_users(2)
        for user in new_students:
            self.assertFalse(self.semester.is_enrolled_student(user))

        response = _patch_semester_request(
            self.semester.pk, self.admin, students_to_add=new_students)
        self.assertEqual(204, response.status_code)

        loaded = Semester.objects.get(pk=self.semester.pk)
        for user in new_students:
            self.assertTrue(loaded.is_enrolled_student(user))

    def test_valid_remove_students(self):
        to_remove = [self.students[1], self.students[3]]
        for user in to_remove:
            self.assertTrue(self.semester.is_enrolled_student(user))

        response = _patch_semester_request(
            self.semester.pk, self.admin, students_to_remove=to_remove)
        self.assertEqual(204, response.status_code)

        loaded = Semester.objects.get(pk=self.semester.pk)
        for user in to_remove:
            self.assertFalse(loaded.is_enrolled_student(user))

    def test_add_students_permission_denied(self):
        new_students = obj_ut.create_dummy_users(2)
        # Staff member (non-admin)
        response = _patch_semester_request(
            self.semester.pk, self.staff[0], students_to_add=new_students)
        self.assertEqual(403, response.status_code)

        # enrolled student
        response = _patch_semester_request(
            self.semester.pk, self.enrolled, students_to_add=new_students)
        self.assertEqual(403, response.status_code)

        # nobody user
        response = _patch_semester_request(
            self.semester.pk, self.nobody, students_to_add=new_students)
        self.assertEqual(403, response.status_code)

    def test_remove_students_permission_denied(self):
        to_remove = [self.students[1], self.students[3]]

        # Staff member (non-admin)
        response = _patch_semester_request(
            self.semester.pk, self.students[0], students_to_remove=to_remove)
        self.assertEqual(403, response.status_code)

        # enrolled student
        response = _patch_semester_request(
            self.semester.pk, self.enrolled, students_to_remove=to_remove)
        self.assertEqual(403, response.status_code)

        # nobody user
        response = _patch_semester_request(
            self.semester.pk, self.nobody, students_to_remove=to_remove)
        self.assertEqual(403, response.status_code)

    def test_invalid_request_add_and_remove_students(self):
        new_students = obj_ut.create_dummy_users(2)
        to_remove = [self.students[1], self.students[3]]

        response = _patch_semester_request(
            self.semester.pk, self.admin,
            students_to_remove=to_remove, students_to_add=new_students)
        self.assertEqual(400, response.status_code)

    # -------------------------------------------------------------------------

    def test_invalid_request_no_metadata(self):
        response = _patch_semester_request(self.semester.pk, self.admin)
        self.assertEqual(400, response.status_code)

    def test_requested_semester_not_found(self):
        bad_semester = obj_ut.create_dummy_semesters(self.course)
        bad_id = bad_semester.pk
        bad_semester.delete()

        response = _patch_semester_request(bad_id, self.admin)
        self.assertEqual(404, response.status_code)


# -----------------------------------------------------------------------------
# -----------------------------------------------------------------------------

# class AddSemesterTestCase(TemporaryFilesystemTestCase):
#     def setUp(self):
#         super().setUp()

#         self.rf = RequestFactory()

#         self.user = obj_ut.create_dummy_users()
#         self.course = obj_ut.create_dummy_courses()

#     def test_valid_add_semester(self):
#         self.course.add_course_admins(self.user)

#         semester_name = 'fall2015'
#         request = self.rf.post(
#             reverse('add-semester'),
#             {"semester_name": semester_name, "course_name": self.course.name})
#         request.user = self.user
#         response = ajax_request_handlers.AddSemester.as_view()(request)

#         self.assertEqual(200, response.status_code)
#         self.assertEqual(
#             {"semester_name": semester_name, "course_name": self.course.name},
#             _bytes_to_json(response.content))

#         loaded_semester = Semester.objects.get(
#             name=semester_name, course=self.course)
#         self.assertEqual(loaded_semester.name, semester_name)
#         self.assertEqual(loaded_semester.course, self.course)

#     def test_add_semester_permission_denied(self):
#         semester_name = 'spam'
#         request = self.rf.post(
#             reverse('add-semester'),
#             {'semester_name': semester_name, 'course_name': self.course.name})
#         request.user = self.user
#         response = ajax_request_handlers.AddSemester.as_view()(request)

#         self.assertEqual(403, response.status_code)

#         with self.assertRaises(ObjectDoesNotExist):
#             Semester.objects.get(name=semester_name, course=self.course)

#     def test_add_duplicate_semester(self):
#         self.course.add_course_admins(self.user)
#         semester = obj_ut.create_dummy_semesters(self.course)

#         request = self.rf.post(
#             reverse('add-semester'),
#             {'semester_name': semester.name, 'course_name': self.course.name})
#         request.user = self.user
#         response = ajax_request_handlers.AddSemester.as_view()(request)

#         self.assertEqual(200, response.status_code)
#         self.assertTrue('errors' in _bytes_to_json(response.content))


# -----------------------------------------------------------------------------
# -----------------------------------------------------------------------------

# class SubmissionRequestTestCase(TemporaryFilesystemTestCase):
#     def setUp(self):
#         self.course = obj_ut.create_dummy_courses()
#         self.semester = obj_ut.create_dummy_semesters(self.course)
#         self.project = obj_ut.create_dummy_projects(self.semester)
#         self.project.max_group_size = 2

#         self.users = obj_ut.create_dummy_users(2)
#         self.submission_group = SubmissionGroup.objects.create_group(
#             members=self.users, project=self.project)

#     def test_submission_requests(self):
#         # create a submission
#         request = self.rf.post(reverse('submission'))
#         request.user = self.users[0]
#         response = ajax_request_handlers.SubmissionHandler.as_view()(request)
#         self.assertEqual(201, response.status_code)
#         content = _bytes_to_json(response.content)

#         # request that submission
#         request = self.rf.get(content['data']['links']['self'])

#         # query for submissions from the same submission group


























