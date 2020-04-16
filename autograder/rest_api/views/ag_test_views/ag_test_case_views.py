from django.db import transaction
from rest_framework import response

import autograder.core.models as ag_models
import autograder.rest_api.permissions as ag_permissions
from autograder.core.caching import clear_submission_results_cache
from autograder.rest_api.schema import (AGDetailViewSchemaGenerator,
                                        AGListCreateViewSchemaGenerator, APITags, OrderViewSchema)
from autograder.rest_api.views.ag_model_views import (AGModelAPIView, AGModelDetailView,
                                                      NestedModelView)


class AGTestCaseListCreateView(NestedModelView):
    schema = AGListCreateViewSchemaGenerator([APITags.ag_test_cases], ag_models.AGTestCase)

    permission_classes = [
        ag_permissions.is_admin_or_read_only_staff(
            lambda ag_test_suite: ag_test_suite.project.course)
    ]

    pk_key = 'ag_test_suite_pk'
    model_manager = ag_models.AGTestSuite.objects.select_related('project__course')
    nested_field_name = 'ag_test_cases'
    parent_obj_field_name = 'ag_test_suite'

    def get(self, *args, **kwargs):
        return self.do_list()

    def post(self, *args, **kwargs):
        return self.do_create()


class AGTestCaseOrderView(AGModelAPIView):
    schema = OrderViewSchema([APITags.ag_test_cases])

    permission_classes = [
        ag_permissions.is_admin_or_read_only_staff(
            lambda ag_test_suite: ag_test_suite.project.course)
    ]

    pk_key = 'ag_test_suite_pk'
    model_manager = ag_models.AGTestSuite.objects.select_related('project__course')
    api_tags = [APITags.ag_test_cases]

    def get(self, request, *args, **kwargs):
        ag_test_suite = self.get_object()
        return response.Response(list(ag_test_suite.get_agtestcase_order()))

    def put(self, request, *args, **kwargs):
        with transaction.atomic():
            ag_test_suite = self.get_object()
            ag_test_suite.set_agtestcase_order(request.data)
            clear_submission_results_cache(ag_test_suite.project_id)
            return response.Response(list(ag_test_suite.get_agtestcase_order()))


class AGTestCaseDetailView(AGModelDetailView):
    schema = AGDetailViewSchemaGenerator([APITags.ag_test_cases])

    permission_classes = [
        ag_permissions.is_admin_or_read_only_staff(
            lambda ag_test_case: ag_test_case.ag_test_suite.project.course
        )
    ]
    model_manager = ag_models.AGTestCase.objects.select_related(
        'ag_test_suite__project__course',
    )

    def get(self, *args, **kwargs):
        return self.do_get()

    def patch(self, *args, **kwargs):
        return self.do_patch()

    def delete(self, *args, **kwargs):
        return self.do_delete()
