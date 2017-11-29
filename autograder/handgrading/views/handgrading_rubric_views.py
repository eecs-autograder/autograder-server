from rest_framework import generics

import autograder.core.models as ag_models
import autograder.handgrading.models as handgrading_models
import autograder.handgrading.serializers as handgrading_serializers
import autograder.rest_api.permissions as ag_permissions

from autograder.rest_api.views.ag_model_views import (
    AGModelGenericViewSet, TransactionRetrieveUpdateDestroyMixin,
)

from autograder.rest_api.transaction_mixins import TransactionCreateMixin, TransactionRetrieveMixin

from autograder.rest_api.views.ag_model_views import (
    GetObjectLockOnUnsafeMixin, AlwaysIsAuthenticatedMixin
)
# class HandgradingRubricListCreateView(ListCreateNestedModelView):
#     serializer_class = handgrading_serializers.HandgradingRubricSerializer
#     permission_classes = [
#         ag_permissions.is_admin_or_read_only_staff(lambda project: project.course)]
#
#     pk_key = 'project_pk'
#     model_manager = ag_models.Project.objects.select_related('course')
#     foreign_key_field_name = 'project'
#     reverse_foreign_key_field_name = 'handgrading_rubric'

class HandgradingRubricRetrieveCreateView(GetObjectLockOnUnsafeMixin,
                                          AlwaysIsAuthenticatedMixin,
                                          TransactionCreateMixin,
                                          TransactionRetrieveMixin,
                                          generics.GenericAPIView):
    one_to_one_field_name = 'project'
    reverse_one_to_one_field_name = 'handgrading_rubric'

    serializer_class = handgrading_serializers.HandgradingRubricSerializer
    permission_classes = [
        ag_permissions.is_admin_or_read_only_staff(lambda project: project.course)]
    pk_key = 'project_pk'
    model_manager = ag_models.Project.objects.select_related('course')

    def get_queryset(self):
        return getattr(self.get_object(), self.reverse_one_to_one_field_name)

    def perform_create(self, serializer):
        serializer.save(**{self.one_to_one_field_name: self.get_object()})

    def get(self, request, *args, **kwargs):
        return self.retrieve(request, *args, **kwargs)

    def post(self, request, *args, **kwargs):
        return self.create(request, *args, **kwargs)


class HandgradingRubricDetailViewSet(TransactionRetrieveUpdateDestroyMixin, AGModelGenericViewSet):
    serializer_class = handgrading_serializers.HandgradingRubricSerializer
    permission_classes = [
        ag_permissions.is_admin_or_read_only_staff(
            lambda handgrading_rubric: handgrading_rubric.project.course)
    ]
    model_manager = handgrading_models.HandgradingRubric.objects.select_related(
        'project__course',
    ).prefetch_related(
        'criteria',
        'annotations'
    )
