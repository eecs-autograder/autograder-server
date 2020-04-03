from rest_framework import permissions

import autograder.core.models as ag_models
import autograder.rest_api.permissions as ag_permissions
import autograder.rest_api.serializers as ag_serializers
from autograder.rest_api.schema import (AGDetailViewSchemaGenerator,
                                        AGListCreateViewSchemaGenerator)
from autograder.rest_api.views.ag_model_views import (AGModelDetailView,
                                                      NestedModelView)
from autograder.rest_api.views.schema_generation import APITags


class ListCreateExpectedStudentFileView(NestedModelView):
    schema = AGListCreateViewSchemaGenerator(
        [APITags.expected_student_files], ag_models.ExpectedStudentFile)

    permission_classes = [ag_permissions.is_admin_or_read_only_can_view_project()]

    model_manager = ag_models.Project.objects
    nested_field_name = 'expected_student_files'
    parent_obj_field_name = 'project'

    def get(self, *args, **kwargs):
        return self.do_list()

    def post(self, *args, **kwargs):
        return self.do_create()


class ExpectedStudentFileDetailView(AGModelDetailView):
    schema = AGDetailViewSchemaGenerator([APITags.expected_student_files])
    permission_classes = [ag_permissions.is_admin_or_read_only_can_view_project()]

    model_manager = ag_models.ExpectedStudentFile.objects

    def get(self, *args, **kwargs):
        return self.do_get()

    def patch(self, *args, **kwargs):
        return self.do_patch()

    def delete(self, *args, **kwargs):
        return self.do_delete()
