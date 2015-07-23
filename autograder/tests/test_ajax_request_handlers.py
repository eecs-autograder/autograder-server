import json

from django.contrib.auth.models import User
from django.test import RequestFactory
from django.core.urlresolvers import reverse_lazy, reverse

from autograder.tests.temporary_filesystem_test_case import (
    TemporaryFilesystemTestCase)

from autograder import ajax_request_handlers

import autograder.tests.dummy_object_utils as obj_ut


def _bytes_to_json(data):
    return json.loads(data.decode('utf-8'))


class CourseRequestHandlerTestCase(TemporaryFilesystemTestCase):
    def setUp(self):
        super().setUp()

        self.rf = RequestFactory()

    def test_list_courses_course_admin(self):
        course_admin = obj_ut.create_dummy_users()
        courses = obj_ut.create_dummy_courses(5)

        courses[1].add_course_admin(course_admin)
        courses[4].add_course_admin(course_admin)

        expected = [
            {
                "name": courses[1].name,
                "admins": [course_admin.username]
            },
            {
                "name": courses[4].name,
                "admins": [course_admin.username]
            }
        ]

        request = self.rf.post(reverse('list-courses'))
        request.user = course_admin
        response = ajax_request_handlers.ListCourses.as_view()(request)

        self.assertEqual(200, response.status_code)
        self.assertEqual(expected, _bytes_to_json(response.content))

    def test_list_courses_empty_list_non_admin(self):
        user = obj_ut.create_dummy_users()
        obj_ut.create_dummy_courses()

        request = self.rf.post(reverse('list-courses'))
        request.user = user
        response = ajax_request_handlers.ListCourses.as_view()(request)

        self.assertEqual(200, response.status_code)
        self.assertEqual([], _bytes_to_json(response.content))

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

    def test_list_semesters_course_admin(self):
        user = obj_ut.create_dummy_users()
        courses = obj_ut.create_dummy_courses(5)

        semesters = (obj_ut.create_dummy_semesters(courses[0], 2) +
                     obj_ut.create_dummy_semesters(courses[3], 3))

        courses[0].add_course_admin(user)
        courses[3].add_course_admin(user)

        expected = [
            {
                "name": semester.name,
                "course_name": semester.course.name,
                "semester_staff": semester.staff_members
            }
            for semester in semesters
        ]

        request = self.rf.post(reverse('list-semesters'))
        request.user = user
        response = ajax_request_handlers.ListSemesters.as_view()(request)

        self.assertEqual(200, response.status_code)
        self.assertEqual(expected, _bytes_to_json(response.content))

    def test_list_semesters_staff_member(self):
        user = obj_ut.create_dummy_users()
        courses = obj_ut.create_dummy_courses(5)

        semesters = (obj_ut.create_dummy_semesters(courses[0], 2) +
                     obj_ut.create_dummy_semesters(courses[3], 3))

        semesters[1].add_semester_staff(user)
        semesters[-1].add_semester_staff(user)

        expected = [
            {
                "name": semester.name,
                "course_name": semester.course.name,
                "semester_staff": semester.staff_members
            }
            for semester in semesters
        ]

        request = self.rf.post(reverse('list-semesters'))
        request.user = user
        response = ajax_request_handlers.ListSemesters.as_view()(request)

        self.assertEqual(200, response.status_code)
        self.assertEqual(expected, _bytes_to_json(response.content))

    def test_list_semesters_enrolled_student(self):
        user = obj_ut.create_dummy_users()
        courses = obj_ut.create_dummy_courses(5)

        semesters = (obj_ut.create_dummy_semesters(courses[0], 2) +
                     obj_ut.create_dummy_semesters(courses[3], 3))

        semesters[0].add_enrolled_student(user)
        semesters[-2].add_enrolled_student(user)

        expected = [
            {
                "name": semester.name,
                "course_name": semester.course.name,
                "semester_staff": semester.staff_members
            }
            for semester in semesters
        ]

        request = self.rf.post(reverse('list-semesters'))
        request.user = user
        response = ajax_request_handlers.ListSemesters.as_view()(request)

        self.assertEqual(200, response.status_code)
        self.assertEqual(expected, _bytes_to_json(response.content))

    def test_list_semesters_enrolled_student_and_semester_staff(self):
        user = obj_ut.create_dummy_users()
        courses = obj_ut.create_dummy_courses(5)

        semesters = (obj_ut.create_dummy_semesters(courses[0], 2) +
                     obj_ut.create_dummy_semesters(courses[3], 3))

        semesters[0].add_semester_staff(user)
        semesters[-2].add_enrolled_student(user)

        expected = [
            {
                "name": semester.name,
                "course_name": semester.course.name,
                "semester_staff": semester.staff_members
            }
            for semester in semesters
        ]

        request = self.rf.post(reverse('list-semesters'))
        request.user = user
        response = ajax_request_handlers.ListSemesters.as_view()(request)

        self.assertEqual(200, response.status_code)
        self.assertEqual(expected, _bytes_to_json(response.content))

    def test_list_semesters_nobody_user(self):
        user = obj_ut.create_dummy_users()
        courses = obj_ut.create_dummy_courses(5)

        obj_ut.create_dummy_semesters(courses[0], 2)
        obj_ut.create_dummy_semesters(courses[3], 3)

        request = self.rf.post(reverse('list-semesters'))
        request.user = user
        response = ajax_request_handlers.ListSemesters.as_view()(request)

        self.assertEqual(200, response.status_code)
        self.assertEqual([], _bytes_to_json(response.content))
