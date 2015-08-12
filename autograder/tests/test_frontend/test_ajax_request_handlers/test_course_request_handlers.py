from autograder.frontend.json_api_serializers import (
    course_to_json, semester_to_json)

import autograder.tests.dummy_object_utils as obj_ut

from .utils import process_get_request, json_load_bytes, RequestHandlerTestCase


class CourseRequestHandlerTestCase(RequestHandlerTestCase):
    def setUp(self):
        super().setUp()

        # self.maxDiff = None

        self.courses = obj_ut.create_dummy_courses(5)

    def test_get_course_as_admin(self):
        course_admin = obj_ut.create_dummy_users()
        course = self.courses[2]

        course.add_course_admins(course_admin)

        response = _get_course_request(course.pk, course_admin)

        self.assertEqual(200, response.status_code)

        content = json_load_bytes(response.content)
        self.assertJSONObjsEqual(
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

        content = json_load_bytes(response.content)
        self.assertJSONObjsEqual(
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
        self.assertJSONObjsEqual(expected, json_load_bytes(response.content))

    def test_list_courses_empty_list_non_admin(self):
        user = obj_ut.create_dummy_users()

        response = _list_courses_request(user)

        expected = {'data': []}

        self.assertEqual(200, response.status_code)
        self.assertJSONObjsEqual(expected, json_load_bytes(response.content))

    # -------------------------------------------------------------------------

    # Move to Django Admin page?

    # def test_add_course_success(self):
    #     self.fail()

    # def test_add_course_permission_denied(self):
    #     self.fail()

    # -------------------------------------------------------------------------

    # def test_add_course_admin_success(self):
    #     self.fail()

    # def test_add_course_admin_permission_denied(self):
    #     self.fail()

    # -------------------------------------------------------------------------

    # def test_remove_course_admin_success(self):
    #     self.fail()

    # def test_remove_course_admin_does_not_exist(self):
    #     self.fail()

    # def test_remove_course_admin_permission_denied(self):
    #     self.fail()


# -----------------------------------------------------------------------------

def _get_course_request(course_id, user):
    url = '/courses/course/{}/'.format(course_id)
    return process_get_request(url, user)


def _list_courses_request(user):
    url = '/courses/'
    return process_get_request(url, user)
