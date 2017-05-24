from rest_framework import request
from rest_framework.test import APIRequestFactory

import autograder.rest_api.serializers as ag_serializers

from .serializer_test_case import SerializerTestCase
import autograder.utils.testing.model_obj_builders as obj_build
from autograder.utils.testing import UnitTestBase

import autograder.rest_api.tests.test_views.common_generic_data as gen_data


class ProjectSerializerTestCase(SerializerTestCase):
    def test_serialize(self):
        project = obj_build.build_project()
        data = self.do_basic_serialize_test(project,
                                            ag_serializers.ProjectSerializer)
        self.assertIn('closing_time', data)


class ClosingTimeShownTestCase(gen_data.Project,
                               UnitTestBase):
    def test_admin_shown_closing_time(self):
        get_request = request.Request(APIRequestFactory().get('path'))
        get_request.user = self.admin
        serializer = ag_serializers.ProjectSerializer(
            self.visible_public_project, context={'request': get_request})

        self.assertIn('closing_time', serializer.data)

    def test_non_admin_not_shown_closing_time(self):
        for user in self.staff, self.enrolled, self.nobody:
            get_request = request.Request(APIRequestFactory().get('path'))
            get_request.user = user
            serializer = ag_serializers.ProjectSerializer(
                self.visible_public_project, context={'request': get_request})

            self.assertNotIn('closing_time', serializer.data)

    def test_non_admin_not_shown_closing_time_even_if_explicitly_requested(self):
        for user in self.staff, self.enrolled, self.nobody:
            query_params = {'include_fields': ['closing_time']}
            get_request = request.Request(
                APIRequestFactory().get('path', data=query_params))
            get_request.user = user
            serializer = ag_serializers.ProjectSerializer(
                self.visible_public_project, context={'request': get_request})

            self.assertNotIn('closing_time', serializer.data)

    def test_serialize_many_closing_time_not_included(self):
        for user in self.admin, self.staff, self.enrolled, self.nobody:
            get_request = request.Request(APIRequestFactory().get('path'))
            get_request.user = user
            serializer = ag_serializers.ProjectSerializer(
                self.all_projects, many=True, context={'request': get_request})

            for item in serializer.data:
                self.assertNotIn('closing_time', item)

    def test_serialize_many_closing_time_not_included_even_if_explicitly_requested(self):
        for user in self.admin, self.staff, self.enrolled, self.nobody:
            query_params = {'include_fields': ['closing_time']}
            get_request = request.Request(
                APIRequestFactory().get('path', data=query_params))
            get_request.user = user
            serializer = ag_serializers.ProjectSerializer(
                self.all_projects, many=True, context={'request': get_request})

            for item in serializer.data:
                self.assertNotIn('closing_time', item)
