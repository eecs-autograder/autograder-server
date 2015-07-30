import json

from django.contrib.auth.models import User
from django.test import RequestFactory
from django.core.urlresolvers import reverse, resolve
from django.core.exceptions import ObjectDoesNotExist

from autograder.tests.temporary_filesystem_test_case import (
    TemporaryFilesystemTestCase)

from autograder import ajax_request_handlers

import autograder.tests.dummy_object_utils as obj_ut

from autograder.models import Semester, SubmissionGroup


def _bytes_to_json(data):
    return json.loads(data.decode('utf-8'))


def _process_get_request(url, user):
    rf = RequestFactory()

    request = rf.get(url)
    request.user = user

    resolved = resolve(request.path)
    return resolved.func(request, *resolved.args, **resolved.kwargs)


def _get_course_request(course_id, user):
    url = '/courses/course/{}/'.format(course_id)
    return _process_get_request(url, user)


def _list_courses_request(user):
    url = '/courses/'
    return _process_get_request(url, user)


class CourseRequestHandlerTestCase(TemporaryFilesystemTestCase):
    def setUp(self):
        super().setUp()

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
                'data': {
                    'type': 'course',
                    'id': course.pk,
                    'attributes': {
                        'name': course.name,
                        'course_admin_names': course.course_admin_names
                    },
                    'links': {
                        'self': reverse('get-course', args=[course.pk])
                    }
                },
                'included': []
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
                {
                    'type': 'course',
                    'id': course.pk,
                    'attributes': {
                        'name': course.name,
                        'course_admin_names': [course_admin.username]
                    },
                    'links': {
                        'self': reverse('get-course', args=[course.pk])
                    }
                } for course in subset
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

class ListSemestersTestCase(TemporaryFilesystemTestCase):
    def setUp(self):
        super().setUp()

        self.rf = RequestFactory()

        self.user = obj_ut.create_dummy_users()
        self.courses = obj_ut.create_dummy_courses(5)

        self.semesters = (obj_ut.create_dummy_semesters(self.courses[0], 2) +
                          obj_ut.create_dummy_semesters(self.courses[3], 3))

    def test_list_semesters_course_admin(self):
        self.courses[0].add_course_admins(self.user)
        self.courses[3].add_course_admins(self.user)

        expected = sorted([
            {
                "name": semester.name,
                "course_name": semester.course.name,
                "semester_staff": semester.semester_staff_names,
                "is_staff": True
            }
            for semester in self.semesters
        ], key=lambda item: item['name'])

        request = self.rf.post(reverse('list-semesters'))
        request.user = self.user
        response = ajax_request_handlers.ListSemesters.as_view()(request)

        self.assertEqual(200, response.status_code)
        self.assertEqual(expected, _bytes_to_json(response.content))

    def test_list_semesters_staff_member(self):
        subset = [self.semesters[1], self.semesters[-1]]
        for semester in subset:
            semester.add_semester_staff(self.user)

        expected = sorted([
            {
                "name": semester.name,
                "course_name": semester.course.name,
                "semester_staff": semester.semester_staff_names,
                "is_staff": True
            }
            for semester in subset
        ], key=lambda item: item['name'])

        request = self.rf.post(reverse('list-semesters'))
        request.user = self.user
        response = ajax_request_handlers.ListSemesters.as_view()(request)

        self.assertEqual(200, response.status_code)
        self.assertEqual(expected, _bytes_to_json(response.content))

    def test_list_semesters_enrolled_student(self):
        subset = [self.semesters[0], self.semesters[-2]]
        for semester in subset:
            semester.add_enrolled_students(self.user)

        expected = sorted([
            {
                "name": semester.name,
                "course_name": semester.course.name,
            }
            for semester in subset
        ], key=lambda item: item['name'])

        request = self.rf.post(reverse('list-semesters'))
        request.user = self.user
        response = ajax_request_handlers.ListSemesters.as_view()(request)

        self.assertEqual(200, response.status_code)
        self.assertEqual(expected, _bytes_to_json(response.content))

    def test_list_semesters_enrolled_student_and_semester_staff(self):
        self.semesters[0].add_semester_staff(self.user)
        self.semesters[-2].add_enrolled_students(self.user)

        expected = sorted([
            {
                "name": self.semesters[0].name,
                "course_name": self.semesters[0].course.name,
                "semester_staff": self.semesters[0].semester_staff_names,
                "is_staff": True
            },
            {
                "name": self.semesters[-2].name,
                "course_name": self.semesters[-2].course.name,
            }
        ], key=lambda item: item['name'])

        request = self.rf.post(reverse('list-semesters'))
        request.user = self.user
        response = ajax_request_handlers.ListSemesters.as_view()(request)

        self.assertEqual(200, response.status_code)
        self.assertEqual(expected, _bytes_to_json(response.content))

    def test_list_semesters_nobody_user(self):
        request = self.rf.post(reverse('list-semesters'))
        request.user = self.user
        response = ajax_request_handlers.ListSemesters.as_view()(request)

        self.assertEqual(200, response.status_code)
        self.assertEqual([], _bytes_to_json(response.content))


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

# class ListSemesterStaffTestCase(TemporaryFilesystemTestCase):
#     def setUp(self):
#         super().setUp()

#         self.rf = RequestFactory()

#         self.user = obj_ut.create_dummy_users()
#         self.course = obj_ut.create_dummy_courses()
#         self.semester = obj_ut.create_dummy_semesters(self.course)

#         self.staff = obj_ut.create_dummy_users(10)

#         self.semester.add_semester_staff(*self.staff)

#     def test_list_semester_staff_valid_course_admin(self):
#         self.course.add_course_admins(self.user)

#         request = self.rf.post(
#             reverse('list-semester-staff'),
#             {'semester_name': self.semester.name,
#              'course_name': self.course.name})
#         request.user = self.user
#         response = ajax_request_handlers.ListSemesterStaff.as_view()(request)

#         expected = {
#             'semester_name': self.semester.name,
#             'course_name': self.course.name,
#             'semester_staff': [user.username for user in self.staff],
#             'course_admins': [self.user.username]
#         }

#         self.assertEqual(200, response.status_code)
#         self.assertEqual(expected, _bytes_to_json(response.content))

#     def test_list_semester_staff_valid_staff_member(self):
#         admin = obj_ut.create_dummy_users()
#         self.course.add_course_admins(admin)

#         request = self.rf.post(
#             reverse('list-semester-staff'),
#             {'semester_name': self.semester.name,
#              'course_name': self.course.name})
#         request.user = self.staff[0]
#         response = ajax_request_handlers.ListSemesterStaff.as_view()(request)

#         expected = {
#             'semester_name': self.semester.name,
#             'course_name': self.course.name,
#             'semester_staff': [user.username for user in self.staff],
#             'course_admins': [admin.username]
#         }

#         self.assertEqual(200, response.status_code)
#         self.assertEqual(expected, _bytes_to_json(response.content))

#     def test_list_semester_staff_permission_denied(self):
#         request = self.rf.post(
#             reverse('list-semester-staff'),
#             {'semester_name': self.semester.name,
#              'course_name': self.course.name})
#         request.user = self.user
#         response = ajax_request_handlers.ListSemesterStaff.as_view()(request)

#         self.assertEqual(403, response.status_code)


# -----------------------------------------------------------------------------
# -----------------------------------------------------------------------------

# class AddSemesterStaffTestCase(TemporaryFilesystemTestCase):
#     def setUp(self):
#         super().setUp()

#         self.rf = RequestFactory()

#         self.user = obj_ut.create_dummy_users()
#         self.course = obj_ut.create_dummy_courses()
#         self.semester = obj_ut.create_dummy_semesters(self.course)

#         self.staff = obj_ut.create_dummy_users(10)
#         self.staff_names = [staffer.username for staffer in self.staff]

#         self.semester.add_semester_staff(*self.staff)

#     def test_valid_add_semester_staff(self):
#         self.course.add_course_admins(self.user)
#         new_staff = obj_ut.create_dummy_users(3)

#         new_staff_names = [staffer.username for staffer in new_staff]

#         request = self.rf.post(
#             reverse('add-semester-staff'),
#             {'semester_name': self.semester.name,
#              'course_name': self.course.name,
#              'new_staff_members': new_staff_names})
#         request.user = self.user
#         response = ajax_request_handlers.AddSemesterStaff.as_view()(request)

#         expected = {
#             'semester_name': self.semester.name,
#             'course_name': self.course.name,
#             'successfully_added': new_staff_names
#         }

#         self.assertEqual(200, response.status_code)
#         self.assertEqual(expected, _bytes_to_json(response.content))

#         self.semester = Semester.objects.get(
#             name=self.semester.name, course=self.course)
#         self.assertEqual(new_staff_names, self.semester.semester_staff_names)

#     # def test_semester_staff_duplicates_ignored(self):
#     #     self.course.add_course_admins(self.user)

#     #     request = self.rf.post(
#     #         reverse('add-semester-staff'),
#     #         {'semester_name': self.semester.name,
#     #          'course_name': self.course.name,
#     #          'new_staff_members': self.staff_names})
#     #     request.user = self.user
#     #     response = ajax_request_handlers.AddSemesterStaff.as_view()(request)

#     #     self.assertEqual(200, response.status_code)
#     #     # content = _bytes_to_json(response.content)
#     #     loaded = Semester.objects.get(pk=self.semester.pk)
#     #     self.assertTrue(loaded.is_semester_staff(self.user))

#     def test_add_semester_staff_permission_denied_for_staff_member(self):
#         self.semester.add_semester_staff(self.user)

#         new_staff = obj_ut.create_dummy_users(6)

#         request = self.rf.post(
#             reverse('add-semester-staff'),
#             {'semester_name': self.semester.name,
#              'course_name': self.course.name,
#              'new_staff_members': [staffer.username for staffer in new_staff]})
#         request.user = self.user
#         response = ajax_request_handlers.AddSemesterStaff.as_view()(request)

#         self.assertEqual(403, response.status_code)

#     def test_add_semester_staff_permission_denied_for_enrolled_student(self):
#         self.semester.add_enrolled_students(self.user)

#         new_staff = obj_ut.create_dummy_users(6)

#         request = self.rf.post(
#             reverse('add-semester-staff'),
#             {'semester_name': self.semester.name,
#              'course_name': self.course.name,
#              'new_staff_members': [staffer.username for staffer in new_staff]})
#         request.user = self.user
#         response = ajax_request_handlers.AddSemesterStaff.as_view()(request)

#         self.assertEqual(403, response.status_code)

#     def test_add_semester_staff_permission_denied_for_normal_user(self):
#         new_staff = obj_ut.create_dummy_users(6)

#         request = self.rf.post(
#             reverse('add-semester-staff'),
#             {'semester_name': self.semester.name,
#              'course_name': self.course.name,
#              'new_staff_members': [staffer.username for staffer in new_staff]})
#         request.user = self.user
#         response = ajax_request_handlers.AddSemesterStaff.as_view()(request)

#         self.assertEqual(403, response.status_code)


# -----------------------------------------------------------------------------
# -----------------------------------------------------------------------------

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


























