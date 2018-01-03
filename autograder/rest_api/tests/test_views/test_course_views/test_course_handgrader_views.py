from django.urls import reverse
from django.contrib.auth.models import User

from rest_framework import status

import autograder.rest_api.serializers as ag_serializers

from autograder.utils.testing import UnitTestBase
import autograder.utils.testing.model_obj_builders as obj_build
import autograder.rest_api.tests.test_views.common_generic_data as test_data
import autograder.rest_api.tests.test_views.common_test_impls as test_impls


class _HandgradersSetUp(test_data.Client, test_data.Course):
    def setUp(self):
        super().setUp()
        self.url = reverse('course-handgraders', kwargs={'pk': self.course.pk})


class ListCourseHandgradersTestCase(_HandgradersSetUp,
                                    test_impls.ListObjectsTest,
                                    UnitTestBase):
    """/api/courses/<pk>/handgraders"""
    def setUp(self):
        super().setUp()

        self.handgraders = obj_build.create_dummy_users(4)
        self.course.handgraders.add(*self.handgraders)

    def test_admin_list_handgraders(self):
        expected_content = ag_serializers.UserSerializer(self.handgraders, many=True).data

        self.do_list_objects_test(self.client, self.admin, self.url, expected_content)

    def test_list_handgraders_permission_denied(self):
        for user in self.enrolled, self.staff, self.handgraders[0], self.nobody:
            self.do_permission_denied_get_test(self.client, user, self.url)


class AddCourseHandgradersTestCase(_HandgradersSetUp, UnitTestBase):
    """/api/courses/<pk>/handgraders"""
    def setUp(self):
        super().setUp()

        self.current_handgraders = obj_build.create_dummy_users(2)
        self.course.handgraders.add(*self.current_handgraders)

    def test_admin_add_handgraders(self):
        self.client.force_authenticate(self.admin)
        new_handgrader_names = (
            ['name1', 'name2'] + [user.username for user in obj_build.create_dummy_users(3)])

        self.assertEqual(len(self.current_handgraders), self.course.handgraders.count())

        response = self.client.patch(self.url, {'new_handgraders': new_handgrader_names})

        new_users = list(User.objects.filter(username__in=new_handgrader_names))

        self.assertEqual(status.HTTP_200_OK, response.status_code)
        self.assertCountEqual(new_users + self.current_handgraders, self.course.handgraders.all())

    def test_add_handgraders_permission_denied(self):
        for user in self.staff, self.current_handgraders[0], self.nobody:
            self.client.force_authenticate(user)
            response = self.client.patch(self.url, {'new_handgraders': ['fake_name']})
            self.assertEqual(status.HTTP_403_FORBIDDEN, response.status_code)

            self.assertCountEqual(self.current_handgraders, self.course.handgraders.all())


class RemoveCourseHandgraderTestCase(_HandgradersSetUp, UnitTestBase):
    """/api/courses/<pk>/handgraders"""
    def setUp(self):
        super().setUp()

        self.remaining_handgraders = obj_build.create_dummy_users(2)
        self.handgraders_to_remove = obj_build.create_dummy_users(5)
        self.all_handgraders = self.remaining_handgraders + self.handgraders_to_remove
        self.total_num_handgraders = len(self.all_handgraders)

        self.course.handgraders.add(*self.all_handgraders)

        self.request_body = {
            "remove_handgraders":
                ag_serializers.UserSerializer(self.handgraders_to_remove, many=True).data
        }

    def test_admin_remove_handgraders(self):
        self.client.force_authenticate(self.admin)
        response = self.client.patch(self.url, self.request_body)
        self.assertEqual(status.HTTP_204_NO_CONTENT, response.status_code)

        self.assertCountEqual(self.remaining_handgraders, self.course.handgraders.all())

    def test_remove_handgraders_permission_denied(self):
        for user in self.staff, self.remaining_handgraders[0], self.nobody:
            self.client.force_authenticate(user)

            response = self.client.patch(self.url, self.request_body)
            self.assertEqual(status.HTTP_403_FORBIDDEN, response.status_code)

            self.assertCountEqual(self.all_handgraders, self.course.handgraders.all())
