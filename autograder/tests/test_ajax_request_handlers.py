import json

from django.contrib.auth.models import User
from django.test import RequestFactory
from django.core.urlresolvers import reverse_lazy, reverse

from autograder.tests.temporary_filesystem_test_case import (
    TemporaryFilesystemTestCase)

from autograder import ajax_request_handlers

import autograder.tests.dummy_object_utils as obj_ut


class CourseRequestHandlerTestCase(TemporaryFilesystemTestCase):
    def setUp(self):
        super().setUp()

        self.rf = RequestFactory()
        # self.course_admin = create_dummy_users()
        # self.superuser = create_dummy_users()

    def test_list_courses_course_admin(self):
        course_admin = obj_ut.create_dummy_users()
        courses = obj_ut.create_dummy_courses(5)

        courses[1].add_course_admin(course_admin)
        courses[4].add_course_admin(course_admin)

        expected = [
            {
                "name": courses[1].name
            },
            {
                "name": courses[4].name
            }
        ]

        request = self.rf.post(reverse('list-courses'))
        request.user = course_admin
        response = ajax_request_handlers.ListCourses.as_view()(request)

        self.assertEqual(200, response.status_code)
        self.assertEqual(expected, json.loads(response.content))

    def test_list_courses_superuser(self):
        self.fail()

    def test_list_courses_permission_denied(self):
        self.fail()

    # -------------------------------------------------------------------------

    def test_add_course_success(self):
        self.fail()

    def test_add_course_permission_denied(self):
        self.fail()

    # -------------------------------------------------------------------------

    def test_add_course_admin_success(self):
        self.fail()

    def test_add_course_admin_permission_denied(self):
        self.fail()

    # -------------------------------------------------------------------------

    def test_remove_course_admin_success(self):
        self.fail()

    def test_remove_course_admin_does_not_exist(self):
        self.fail()

    def test_remove_course_admin_permission_denied(self):
        self.fail()

    # -------------------------------------------------------------------------

