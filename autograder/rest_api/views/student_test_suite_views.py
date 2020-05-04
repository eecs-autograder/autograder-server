from django.db import transaction
from django.db.models.signals import post_delete, post_save
from django.dispatch import receiver
from rest_framework import response
from rest_framework.views import APIView

import autograder.core.models as ag_models
import autograder.rest_api.permissions as ag_permissions
from autograder.core.caching import clear_submission_results_cache
from autograder.rest_api.schema import (AGDetailViewSchemaGenerator,
                                        AGListCreateViewSchemaGenerator, APITags, OrderViewSchema)
from autograder.rest_api.views.ag_model_views import (AGModelAPIView, AGModelDetailView,
                                                      NestedModelView)


class MutationTestSuiteListCreateView(NestedModelView):
    schema = AGListCreateViewSchemaGenerator(
        [APITags.student_test_suites], ag_models.MutationTestSuite)

    permission_classes = [
        ag_permissions.is_admin_or_read_only_staff(lambda project: project.course)]

    pk_key = 'project_pk'
    model_manager = ag_models.Project.objects.select_related('course')
    nested_field_name = 'student_test_suites'
    parent_obj_field_name = 'project'

    def get(self, *args, **kwargs):
        return self.do_list()

    def post(self, *args, **kwargs):
        return self.do_create()


class MutationTestSuiteOrderView(AGModelAPIView):
    schema = OrderViewSchema([APITags.student_test_suites], ag_models.MutationTestSuite)

    permission_classes = [
        ag_permissions.is_admin_or_read_only_staff(lambda project: project.course)]

    pk_key = 'project_pk'
    model_manager = ag_models.Project.objects.select_related('course')

    def get(self, *args, **kwargs):
        project = self.get_object()
        return response.Response(list(project.get_mutationtestsuite_order()))

    def put(self, request, *args, **kwargs):
        with transaction.atomic():
            project = self.get_object()
            project.set_mutationtestsuite_order(request.data)
            clear_submission_results_cache(project.pk)
            return response.Response(list(project.get_mutationtestsuite_order()))


class MutationTestSuiteDetailView(AGModelDetailView):
    schema = AGDetailViewSchemaGenerator([APITags.student_test_suites])

    permission_classes = [
        ag_permissions.is_admin_or_read_only_staff(
            lambda student_suite: student_suite.project.course)]

    model_manager = ag_models.MutationTestSuite.objects

    def get(self, *args, **kwargs):
        return self.do_get()

    def patch(self, *args, **kwargs):
        return self.do_patch()

    def delete(self, *args, **kwargs):
        return self.do_delete()
