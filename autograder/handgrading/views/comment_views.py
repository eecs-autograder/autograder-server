from typing import Any, Callable

from rest_framework import permissions

import autograder.handgrading.models as hg_models
from autograder.rest_api.schema import (AGDetailViewSchemaGenerator,
                                        AGListCreateViewSchemaGenerator, APITags)
from autograder.rest_api.views.ag_model_views import AGModelDetailView, NestedModelView

GetRubricFnType = Callable[[Any], hg_models.HandgradingRubric]


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

            return (
                is_admin
                or is_staff
                or (can_edit and is_handgrader)
                or (read_only and is_handgrader)
            )

    return CommentPermissions


class ListCreateCommentView(NestedModelView):
    schema = AGListCreateViewSchemaGenerator(
        [APITags.comments], hg_models.Comment)
    permission_classes = [comment_permissions(lambda result: result.handgrading_rubric)]

    pk_key = 'handgrading_result_pk'
    model_manager = hg_models.HandgradingResult.objects.select_related(
        'handgrading_rubric__project__course')
    nested_field_name = 'comments'
    parent_obj_field_name = 'handgrading_result'

    def get(self, *args, **kwargs):
        return self.do_list()

    def post(self, *args, **kwargs):
        return self.do_create()


class CommentDetailView(AGModelDetailView):
    schema = AGDetailViewSchemaGenerator([APITags.comments])
    permission_classes = [
        comment_permissions(lambda comment: comment.handgrading_result.handgrading_rubric)
    ]
    model_manager = hg_models.Comment.objects.select_related(
        'handgrading_result__handgrading_rubric__project__course'
    )

    def get(self, *args, **kwargs):
        return self.do_get()

    def patch(self, *args, **kwargs):
        return self.do_patch()

    def delete(self, *args, **kwargs):
        return self.do_delete()
