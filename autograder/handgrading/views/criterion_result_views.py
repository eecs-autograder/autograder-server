import autograder.handgrading.models as hg_models
import autograder.rest_api.permissions as ag_permissions
from autograder.rest_api.schema import (AGDetailViewSchemaGenerator,
                                        AGListCreateViewSchemaGenerator, APITags, OrderViewSchema)
from autograder.rest_api.views.ag_model_views import AGModelDetailView, NestedModelView


class ListCreateCriterionResultView(NestedModelView):
    schema = AGListCreateViewSchemaGenerator(
        [APITags.criterion_results], hg_models.CriterionResult)

    permission_classes = [
        ag_permissions.is_admin_or_staff_or_handgrader(
            lambda handgrading_result: handgrading_result.handgrading_rubric.project.course)]

    pk_key = 'handgrading_result_pk'
    model_manager = hg_models.HandgradingResult.objects.select_related(
        'handgrading_rubric__project__course')
    nested_field_name = 'criterion_results'
    parent_obj_field_name = 'handgrading_result'

    def get(self, *args, **kwargs):
        return self.do_list()

    def post(self, *args, **kwargs):
        return self.do_create()


class CriterionResultDetailView(AGModelDetailView):
    schema = AGDetailViewSchemaGenerator([APITags.criterion_results])

    permission_classes = [
        ag_permissions.is_admin_or_staff_or_handgrader(
            lambda criterion_result: (
                criterion_result.handgrading_result.handgrading_rubric.project.course)
        )
    ]
    model_manager = hg_models.CriterionResult.objects.select_related(
        'handgrading_result__handgrading_rubric__project__course'
    ).prefetch_related(
        'criterion'
    )

    def get(self, *args, **kwargs):
        return self.do_get()

    def patch(self, *args, **kwargs):
        return self.do_patch()

    def delete(self, *args, **kwargs):
        return self.do_delete()
