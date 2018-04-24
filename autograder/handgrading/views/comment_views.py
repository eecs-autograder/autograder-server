from typing import Any, Callable

from rest_framework import permissions

import autograder.handgrading.models as handgrading_models
import autograder.handgrading.serializers as handgrading_serializers
from autograder.rest_api.views.ag_model_views import (
    AGModelGenericViewSet, ListCreateNestedModelViewSet, TransactionRetrievePatchDestroyMixin,
)

GetRubricFnType = Callable[[Any], handgrading_models.HandgradingRubric]


def comment_permissions(get_course_fn: GetRubricFnType=lambda rubric: rubric):
    class CommentPermissions(permissions.BasePermission):
        def has_object_permission(self, request, view, obj):
            rubric = get_course_fn(obj)
            course = rubric.project.course
            can_edit = rubric.handgraders_can_leave_comments

            is_admin = course.is_admin(request.user)
            is_staff = course.is_staff(request.user)
            is_handgrader = course.is_handgrader(request.user)
            read_only = request.method in permissions.SAFE_METHODS

            return is_admin or (is_handgrader and can_edit) or (read_only and (is_staff
                                                                               or is_handgrader))
    return CommentPermissions


class CommentListCreateView(ListCreateNestedModelViewSet):
    serializer_class = handgrading_serializers.CommentSerializer
    permission_classes = [
        comment_permissions(
            lambda result: result.handgrading_rubric)]

    pk_key = 'handgrading_result_pk'
    model_manager = handgrading_models.HandgradingResult.objects.select_related(
        'handgrading_rubric__project__course')
    to_one_field_name = 'handgrading_result'
    reverse_to_one_field_name = 'comments'


class CommentDetailViewSet(TransactionRetrievePatchDestroyMixin, AGModelGenericViewSet):
    serializer_class = handgrading_serializers.CommentSerializer
    permission_classes = [
        comment_permissions(
            lambda comment: comment.handgrading_result.handgrading_rubric)]
    model_manager = handgrading_models.Comment.objects.select_related(
        'handgrading_result__handgrading_rubric__project__course'
    )
