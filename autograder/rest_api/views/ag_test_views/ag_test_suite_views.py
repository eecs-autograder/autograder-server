from django.db import transaction
from django.db.models import Prefetch
from rest_framework import response

import autograder.core.models as ag_models
import autograder.rest_api.permissions as ag_permissions
from autograder.core.caching import clear_submission_results_cache
from autograder.rest_api.schema import (AGDetailViewSchemaGenerator,
                                        AGListCreateViewSchemaGenerator,
                                        APITags, CustomViewSchema,
                                        OrderViewSchema)
from autograder.rest_api.views.ag_model_views import (AGModelAPIView,
                                                      AGModelDetailView,
                                                      NestedModelView)


class AGTestSuiteListCreateView(NestedModelView):
    schema = AGListCreateViewSchemaGenerator([APITags.ag_test_suites], ag_models.AGTestSuite)

    permission_classes = [
        ag_permissions.is_admin_or_read_only_staff(lambda project: project.course)]

    pk_key = 'project_pk'
    model_manager = ag_models.Project.objects.select_related('course').prefetch_related(
        Prefetch(
            'ag_test_suites',
            ag_models.AGTestSuite.objects.select_related(
                'project__course',
            ).prefetch_related(
                Prefetch('instructor_files_needed',
                         ag_models.InstructorFile.objects.select_related('project')),
                Prefetch('student_files_needed',
                         ag_models.ExpectedStudentFile.objects.select_related('project')),
                Prefetch(
                    'ag_test_cases',
                    ag_models.AGTestCase.objects.select_related(
                        'ag_test_suite',
                    ).prefetch_related(
                        Prefetch(
                            'ag_test_commands',
                            ag_models.AGTestCommand.objects.select_related('ag_test_case')
                        )
                    )
                )
            )
        )
    )
    nested_field_name = 'ag_test_suites'
    parent_obj_field_name = 'project'

    def get(self, *args, **kwargs):
        return self.do_list()

    def post(self, *args, **kwargs):
        return self.do_create()


class AGTestSuiteOrderView(AGModelAPIView):
    schema = OrderViewSchema([APITags.ag_test_suites])

    permission_classes = [
        ag_permissions.is_admin_or_read_only_staff(lambda project: project.course)
    ]

    pk_key = 'project_pk'
    model_manager = ag_models.Project.objects.select_related('course')

    def get(self, *args, **kwargs):
        project = self.get_object()
        return response.Response(list(project.get_agtestsuite_order()))

    def put(self, request, *args, **kwargs):
        with transaction.atomic():
            project = self.get_object()
            project.set_agtestsuite_order(request.data)
            clear_submission_results_cache(project.pk)
            return response.Response(list(project.get_agtestsuite_order()))


class AGTestSuiteDetailView(AGModelDetailView):
    schema = AGDetailViewSchemaGenerator([APITags.ag_test_suites])

    permission_classes = [
        ag_permissions.is_admin_or_read_only_staff(
            lambda ag_test_suite: ag_test_suite.project.course)
    ]
    model_manager = ag_models.AGTestSuite.objects.select_related(
        'project__course',
    )

    def get(self, *args, **kwargs):
        return self.do_get()

    def patch(self, *args, **kwargs):
        return self.do_patch()

    def delete(self, *args, **kwargs):
        return self.do_delete()
