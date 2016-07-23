from django.contrib.auth.models import User
from django.utils import timezone

from rest_framework import viewsets, mixins, permissions, decorators, response

import autograder.core.models as ag_models
import autograder.rest_api.serializers as ag_serializers

from .permission_components import user_can_view_group
from .load_object_mixin import build_load_object_mixin


class _Permissions(permissions.BasePermission):
    def has_object_permission(self, request, view, result):
        group = result.submission.submission_group
        if not user_can_view_group(request.user, group):
            return False

        student_view = request.query_params.get('student_view', False)
        project = group.project
        course = project.course

        if course.is_course_staff(request.user):
            if (not student_view or
                    not group.members.filter(pk=request.user.pk).exists()):
                return True

        deadline_past = (project.closing_time is None or
                         timezone.now() > project.closing_time)
        if (result.submission == group.ultimate_submission and
                not project.hide_ultimate_submission_fdbk and
                deadline_past):
            return result.test_case.visible_in_ultimate_submission

        if result.submission.is_past_daily_limit:
            return result.test_case.visible_in_past_limit_submission

        return result.test_case.visible_to_students


class AGTestResultViewSet(
        build_load_object_mixin(ag_models.AutograderTestCaseResult),
        mixins.RetrieveModelMixin,
        viewsets.GenericViewSet):
    queryset = ag_models.AutograderTestCaseResult.objects.all()
    serializer_class = ag_serializers.AGTestResultSerializer
    permission_classes = (permissions.IsAuthenticated, _Permissions)
