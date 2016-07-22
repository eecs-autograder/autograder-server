from rest_framework import request
from rest_framework.test import APIRequestFactory

import autograder.core.models as ag_models

import autograder.rest_api.serializers as ag_serializers

from .serializer_test_case import SerializerTestCase
import autograder.core.tests.dummy_object_utils as obj_ut


class AGTestResultSerializerTestCase(SerializerTestCase):
    def test_serialize(self):
        fdbk = obj_ut.random_fdbk()
        result = obj_ut.build_compiled_ag_test_result(
            ag_test_kwargs={'feedback_configuration': fdbk})

        serializer = ag_serializers.AGTestResultSerializer(result)
        self.assertEqual(result.get_feedback().to_dict(), serializer.data)

    def test_user_taken_from_request(self):
        result, admin = self.make_result_and_admin()

        get_request = request.Request(APIRequestFactory().get('path'))
        get_request.user = admin

        actual_data = ag_serializers.AGTestResultSerializer(
            result, context={'request': get_request}).data

        result.test_case.validate_and_update(
            feedback_configuration=(
                ag_models.FeedbackConfig.create_with_max_fdbk()))

        self.assertEqual(result.get_feedback().to_dict(), actual_data)

    def test_student_view_taken_from_request(self):
        result, admin = self.make_result_and_admin()

        get_request = request.Request(
            APIRequestFactory().get('path', data={'student_view': True}))
        request.user = admin

        actual_data = ag_serializers.AGTestResultSerializer(
            result, context={'request': get_request}).data

        self.assertEqual(result.get_feedback().to_dict(), actual_data)

    def make_result_and_admin(self):
        result = obj_ut.build_compiled_ag_test_result()
        group = result.submission.submission_group
        course = group.project.course
        admin = obj_ut.create_dummy_user()
        course.administrators.add(admin)

        group.members.set([admin], clear=True)

        self.assertTrue(course.is_course_staff(admin))
        return result, admin
