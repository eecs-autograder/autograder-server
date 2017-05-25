from django.contrib.auth.models import User
from django.utils import timezone

from rest_framework import viewsets, mixins, permissions, decorators, response

import autograder.core.models as ag_models
import autograder.rest_api.serializers as ag_serializers
from autograder.rest_api import transaction_mixins

from autograder import utils
import autograder.utils.testing as test_ut

from ..permission_components import user_can_view_group
from ..load_object_mixin import build_load_object_mixin


class _Permissions(permissions.BasePermission):
    def has_object_permission(self, request, view, group):
        if request.method not in permissions.SAFE_METHODS:
            return group.project.course.is_administrator(request.user)

        return user_can_view_group(request.user, group)


class _UltimateSubmissionPermissions(_Permissions):
    def has_object_permission(self, request, view, group):
        if not super().has_object_permission(request, view, group):
            return False

        project = group.project
        course = group.project.course
        is_staff = course.is_course_staff(request.user)
        # Staff and higher can always view their own ultimate submission
        if is_staff and group.members.filter(pk=request.user.pk).exists():
            return True

        closing_time = (project.closing_time if group.extended_due_date is None
                        else group.extended_due_date)
        closing_time_passed = (closing_time is None or
                               timezone.now() > closing_time)
        if not closing_time_passed:
            return False

        # If closing time has passed, staff can view anyone's ultimate
        if is_staff:
            return True

        return not project.hide_ultimate_submission_fdbk


class GroupDetailViewSet(build_load_object_mixin(ag_models.SubmissionGroup),
                         mixins.RetrieveModelMixin,
                         transaction_mixins.TransactionUpdateMixin,
                         viewsets.GenericViewSet):
    queryset = ag_models.SubmissionGroup.objects.all()
    serializer_class = ag_serializers.SubmissionGroupSerializer
    permission_classes = (permissions.IsAuthenticated, _Permissions)

    def update(self, request, *args, **kwargs):
        if 'member_names' in request.data:
            users = [
                User.objects.get_or_create(
                    username=username)[0]
                for username in request.data.pop('member_names')]

            utils.lock_users(users)
            # Keep this hook just after the users are locked
            test_ut.mocking_hook()

            request.data['members'] = users
            request.data['check_group_size_limits'] = False
        return super().update(request, *args, **kwargs)

    @decorators.detail_route(permission_classes=(
        permissions.IsAuthenticated, _UltimateSubmissionPermissions))
    def ultimate_submission(self, request, *args, **kwargs):
        '''
        Permissions details:
        - The normal group and submission viewing permissions apply
          first.
        - Staff members can always view their own ultimate submission.
        - Staff members can only view student and other staff ultimate
          submissions if the project closing time has passed.
        - If the project closing time has passed, staff can view student
          and other staff ultimate submissions regardless of whether
          ultimate submissions are marked as hidden.
        - Students can view their ultimate submissions as long as the
          closing time has passed and ultimate submissions are not
          overridden as being hidden.
        '''
        group = self.get_object()
        content = ag_serializers.SubmissionSerializer(
            group.ultimate_submission).data
        return response.Response(content)
