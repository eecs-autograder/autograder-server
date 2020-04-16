from django.core.exceptions import ObjectDoesNotExist
from django.db import transaction
from django.http import Http404
from drf_composable_permissions.p import P
from rest_framework import response, status

import autograder.core.models as ag_models
import autograder.handgrading.models as hg_models
import autograder.rest_api.permissions as ag_permissions
from autograder.rest_api.schema import (AGCreateViewSchemaMixin, AGDetailViewSchemaGenerator,
                                        AGRetrieveViewSchemaMixin, AGViewSchemaGenerator, APITags)
from autograder.rest_api.views.ag_model_views import (AGModelAPIView, AGModelDetailView,
                                                      convert_django_validation_error)

is_admin_or_read_only = ag_permissions.is_admin_or_read_only_staff(lambda project: project.course)
is_handgrader = ag_permissions.is_handgrader(lambda project: project.course)


class _GetCreateHandgradingRubricSchema(
    AGRetrieveViewSchemaMixin, AGCreateViewSchemaMixin, AGViewSchemaGenerator
):
    pass


class GetCreateHandgradingRubricView(AGModelAPIView):
    schema = _GetCreateHandgradingRubricSchema(
        [APITags.handgrading_rubrics], hg_models.HandgradingRubric)

    permission_classes = [
        P(is_admin_or_read_only) | (P(is_handgrader) & P(ag_permissions.IsReadOnly))
    ]

    pk_key = 'project_pk'
    model_manager = ag_models.Project.objects.select_related('course')
    nested_field_name = 'handgrading_rubric'
    parent_obj_field_name = 'project'

    def get(self, *args, **kwargs):
        project = self.get_object()
        try:
            handgrading_rubric = project.handgrading_rubric
        except ObjectDoesNotExist:
            raise Http404(
                f'Project "{project.name}" has no HandgradingRubric (handgrading not enabled)'
            )

        return response.Response(handgrading_rubric.to_dict())

    @convert_django_validation_error
    @transaction.atomic
    def post(self, *args, **kwargs):
        data = dict(self.request.data)
        data[self.parent_obj_field_name] = self.get_object()

        rubric = hg_models.HandgradingRubric.objects.validate_and_create(**data)
        return response.Response(rubric.to_dict(), status.HTTP_201_CREATED)


class HandgradingRubricDetailView(AGModelDetailView):
    schema = AGDetailViewSchemaGenerator([APITags.handgrading_rubrics])

    permission_classes = [
        ag_permissions.is_admin_or_read_only_staff(
            lambda handgrading_rubric: handgrading_rubric.project.course)
    ]
    model_manager = hg_models.HandgradingRubric.objects.select_related(
        'project__course',
    ).prefetch_related(
        'criteria',
        'annotations'
    )

    def get(self, *args, **kwargs):
        return self.do_get()

    def patch(self, *args, **kwargs):
        return self.do_patch()

    def delete(self, *args, **kwargs):
        return self.do_delete()
