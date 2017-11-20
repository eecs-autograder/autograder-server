from django.db import transaction

from rest_framework import generics, response

import autograder.core.models as ag_models
import autograder.rest_api.serializers as ag_serializers
import autograder.rest_api.permissions as ag_permissions

from autograder.rest_api.views.ag_model_views import (
    AGModelGenericViewSet, ListCreateNestedModelView, TransactionRetrieveUpdateDestroyMixin,
    GetObjectLockOnUnsafeMixin)


class StudentTestSuiteListCreateView(ListCreateNestedModelView):
    serializer_class = ag_serializers.StudentTestSuiteSerializer
    permission_classes = [
        ag_permissions.is_admin_or_read_only_staff(lambda project: project.course)]

    pk_key = 'project_pk'
    model_manager = ag_models.Project.objects.select_related('course')
    foreign_key_field_name = 'project'
    reverse_foreign_key_field_name = 'student_test_suites'


class StudentTestSuiteOrderView(GetObjectLockOnUnsafeMixin, generics.GenericAPIView):
    permission_classes = [
        ag_permissions.is_admin_or_read_only_staff(lambda project: project.course)]

    pk_key = 'project_pk'
    model_manager = ag_models.Project.objects.select_related('course')

    def get(self, *args, **kwargs):
        project = self.get_object()
        return response.Response(list(project.get_studenttestsuite_order()))

    def put(self, request, *args, **kwargs):
        with transaction.atomic():
            project = self.get_object()
            project.set_studenttestsuite_order(request.data)
            return response.Response(list(project.get_studenttestsuite_order()))


class StudentTestSuiteDetailViewSet(TransactionRetrieveUpdateDestroyMixin, AGModelGenericViewSet):
    serializer_class = ag_serializers.StudentTestSuiteSerializer
    permission_classes = [
        ag_permissions.is_admin_or_read_only_staff(
            lambda student_suite: student_suite.project.course)]

    model_manager = ag_models.StudentTestSuite.objects
