from django.db import transaction
from django.db.models.signals import post_delete, post_save
from django.dispatch import receiver
from rest_framework import response

import autograder.core.models as ag_models
import autograder.rest_api.permissions as ag_permissions
from autograder.core.caching import clear_submission_results_cache
from autograder.rest_api.schema import (AGDetailViewSchemaGenerator,
                                        AGListCreateViewSchemaGenerator, APITags, OrderViewSchema)
from autograder.rest_api.views.ag_model_views import (AGModelAPIView, AGModelDetailView,
                                                      NestedModelView)


class AGTestCommandListCreateView(NestedModelView):
    schema = AGListCreateViewSchemaGenerator([APITags.ag_test_commands], ag_models.AGTestCommand)

    permission_classes = [
        ag_permissions.is_admin_or_read_only_staff(
            lambda ag_test_case: ag_test_case.ag_test_suite.project.course)
    ]

    pk_key = 'ag_test_case_pk'
    model_manager = ag_models.AGTestCase.objects.select_related('ag_test_suite__project__course')
    nested_field_name = 'ag_test_commands'
    parent_obj_field_name = 'ag_test_case'

    def get(self, *args, **kwargs):
        return self.do_list()

    def post(self, *args, **kwargs):
        return self.do_create()


class AGTestCommandOrderView(AGModelAPIView):
    schema = OrderViewSchema([APITags.ag_test_commands])

    permission_classes = [
        ag_permissions.is_admin_or_read_only_staff(
            lambda ag_test_case: ag_test_case.ag_test_suite.project.course)
    ]

    pk_key = 'ag_test_case_pk'
    model_manager = ag_models.AGTestCase.objects.select_related('ag_test_suite__project__course')
    api_tags = [APITags.ag_test_commands]

    def get(self, request, *args, **kwargs):
        ag_test_case = self.get_object()
        return response.Response(list(ag_test_case.get_agtestcommand_order()))

    def put(self, request, *args, **kwargs):
        with transaction.atomic():
            ag_test_case = self.get_object()
            ag_test_case.set_agtestcommand_order(request.data)
            clear_submission_results_cache(ag_test_case.ag_test_suite.project_id)
            return response.Response(list(ag_test_case.get_agtestcommand_order()))


class AGTestCommandDetailView(AGModelDetailView):
    schema = AGDetailViewSchemaGenerator([APITags.ag_test_commands])

    permission_classes = [
        ag_permissions.is_admin_or_read_only_staff(
            lambda ag_test_command: ag_test_command.ag_test_case.ag_test_suite.project.course
        )
    ]
    model_manager = ag_models.AGTestCommand.objects.select_related(
        'ag_test_case__ag_test_suite__project__course',
    )

    def get(self, *args, **kwargs):
        return self.do_get()

    def patch(self, *args, **kwargs):
        return self.do_patch()

    def delete(self, *args, **kwargs):
        return self.do_delete()
