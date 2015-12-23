import itertools

from django.core.urlresolvers import reverse

from autograder.core.tests.temporary_filesystem_test_case import (
    TemporaryFilesystemTestCase)
import autograder.core.tests.dummy_object_utils as obj_ut
from .utilities import MockClient, json_load_bytes, sorted_by_pk


class UserGetRequestTestCase(TemporaryFilesystemTestCase):
    def setUp(self):
        super().setUp()

        self.maxDiff = None

        self.administrator = obj_ut.create_dummy_user()
        self.staff = obj_ut.create_dummy_user()
        self.not_enrolled = obj_ut.create_dummy_user()

        self.group = obj_ut.build_submission_group(
            num_members=2, semester_kwargs={'staff': [self.staff]},
            course_kwargs={'administrators': [self.administrator]})

        self.enrolled_users = list(self.group.members.all())

    def test_user_get_self_all_info_returned(self):
        for user in self.enrolled_users:
            client = MockClient(user)

            expected_json = {
                "type": "user",
                "id": user.pk,
                "username": user.username,

                "urls": {
                    "self": reverse('user:get', kwargs={'pk': user.pk}),

                    "courses_is_admin_for": reverse(
                        'user:admin-courses', kwargs={'pk': user.pk}),
                    "semesters_is_staff_for": reverse(
                        'user:staff-semesters', kwargs={'pk': user.pk}),
                    "semesters_is_enrolled_in": reverse(
                        'user:enrolled-semesters', kwargs={'pk': user.pk}),
                    "groups_is_member_of": reverse(
                        'user:submission-groups', kwargs={'pk': user.pk}),

                    "pending_group_requests": reverse(
                        'user:pending-group-requests', kwargs={'pk': user.pk}),

                    "notifications": reverse(
                        'user:notifications', kwargs={'pk': user.pk})
                }
            }
            response = client.get(reverse('user:get', kwargs={'pk': user.pk}))

            self.assertEqual(200, response.status_code)
            self.assertEqual(expected_json, json_load_bytes(response.content))

    def test_other_get_user_minimum_info_returned(self):
        users = self.enrolled_users + [
            self.administrator, self.staff, self.not_enrolled]
        for requester, requested in itertools.product(users, users):
            if requester == requested:
                continue

            client = MockClient(requester)

            expected_json = {
                "type": "user",
                "id": requested.pk,
                "username": requested.username,

                "urls": {
                    "self": reverse('user:get', kwargs={'pk': requested.pk}),
                }
            }
            response = client.get(
                reverse('user:get', kwargs={'pk': requested.pk}))

            self.assertEqual(200, response.status_code)
            self.assertEqual(expected_json, json_load_bytes(response.content))

    def test_user_not_found(self):
        client = MockClient(self.administrator)

        response = client.get(
            reverse('user:get', kwargs={'pk': 750}))

        self.assertEqual(404, response.status_code)

    # -------------------------------------------------------------------------

    def test_user_get_self_courses_is_admin_for(self):
        other_course = obj_ut.build_course()
        other_course.administrators.add(self.administrator)

        client = MockClient(self.administrator)

        expected_json = {
            "courses": [
                {
                    "type": 'course',
                    'id': course.pk,
                    'name': course.name,
                    'urls': {
                        'self': reverse('course:get', kwargs={'pk': course.pk})
                    }
                }
                for course in sorted_by_pk(
                    self.administrator.courses_is_admin_for.all())
            ]
        }

        response = client.get(
            reverse(
                'user:admin-courses', kwargs={'pk': self.administrator.pk}))

        self.assertEqual(200, response.status_code)

        actual_json = json_load_bytes(response.content)
        actual_json['courses'] = sorted_by_pk(actual_json['courses'])

        self.assertEqual(expected_json, actual_json)

    def test_permission_denied_get_other_courses_is_admin_for(self):
        self.fail()

    def test_user_get_self_semesters_is_staff_for(self):
        self.fail()

    def test_permission_denied_get_other_semesters_is_staff_for(self):
        self.fail()

    def test_user_get_self_semesters_is_enrolled_in(self):
        self.fail()

    def test_permission_denied_get_other_semesters_is_enrolled_in(self):
        self.fail()

    def test_user_get_self_groups_is_member_of(self):
        self.fail()

    def test_permission_denied_get_other_groups_is_member_of(self):
        self.fail()

    def test_user_get_self_pending_group_requests(self):
        self.fail()

    def test_permission_denied_get_other_pending_group_requests(self):
        self.fail()

    def test_user_get_self_notifications(self):
        self.fail()

    def test_permission_denied_get_other_notifications(self):
        self.fail()
