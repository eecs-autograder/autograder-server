from django.db import transaction
from django.db.models.signals import post_save, post_delete
from django.dispatch import receiver
# from drf_yasg.openapi import Parameter
# from drf_yasg.utils import swagger_auto_schema
from rest_framework import response
from rest_framework.views import APIView

import autograder.core.models as ag_models
import autograder.rest_api.permissions as ag_permissions
import autograder.rest_api.serializers as ag_serializers
from autograder.core.caching import clear_submission_results_cache
from autograder.rest_api.views.ag_model_views import (
    AGModelGenericViewSet, ListCreateNestedModelViewSet, TransactionRetrievePatchDestroyMixin,
    GetObjectLockOnUnsafeMixin, AGModelAPIView)
from autograder.rest_api.views.schema_generation import APITags


class StudentTestSuiteListCreateView(ListCreateNestedModelViewSet):
    serializer_class = ag_serializers.StudentTestSuiteSerializer
    permission_classes = [
        ag_permissions.is_admin_or_read_only_staff(lambda project: project.course)]

    pk_key = 'project_pk'
    model_manager = ag_models.Project.objects.select_related('course')
    to_one_field_name = 'project'
    reverse_to_one_field_name = 'student_test_suites'


class StudentTestSuiteOrderView(AGModelAPIView):
    permission_classes = [
        ag_permissions.is_admin_or_read_only_staff(lambda project: project.course)]

    pk_key = 'project_pk'
    model_manager = ag_models.Project.objects.select_related('course')
    api_tags = [APITags.student_test_suites]

    # @swagger_auto_schema(
    #     responses={'200': 'Returns a list of StudentTestSuite IDs, in their assigned order.'})
    def get(self, *args, **kwargs):
        project = self.get_object()
        return response.Response(list(project.get_studenttestsuite_order()))

    # @swagger_auto_schema(
    #     request_body_parameters=[
    #         Parameter(name='', in_='body',
    #                   type='List[string]',
    #                   description='A list of StudentTestSuite IDs, in the new order to set.')],
    #     responses={'200': 'Returns a list of StudentTestSuite IDs, in their new order.'}
    # )
    def put(self, request, *args, **kwargs):
        with transaction.atomic():
            project = self.get_object()
            project.set_studenttestsuite_order(request.data)
            clear_submission_results_cache(project.pk)
            return response.Response(list(project.get_studenttestsuite_order()))


class StudentTestSuiteDetailViewSet(TransactionRetrievePatchDestroyMixin, AGModelGenericViewSet):
    serializer_class = ag_serializers.StudentTestSuiteSerializer
    permission_classes = [
        ag_permissions.is_admin_or_read_only_staff(
            lambda student_suite: student_suite.project.course)]

    model_manager = ag_models.StudentTestSuite.objects
