import tempfile
import os
import shutil
import itertools

from django.contrib.auth.models import User
from django.utils import timezone
from django.db import transaction

from rest_framework import viewsets, mixins, permissions, decorators, response

import autograder.core.models as ag_models
import autograder.rest_api.serializers as ag_serializers
from autograder.rest_api import transaction_mixins

from autograder import utils
import autograder.utils.testing as test_ut
import autograder.core.utils as core_ut

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


class GroupViewset(build_load_object_mixin(ag_models.SubmissionGroup),  # type: ignore
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

    @decorators.detail_route()
    @transaction.atomic()
    def merge_with(self, request, *args, **kwargs):
        group1 = self.get_object()
        group2 = ag_models.SubmissionGroup.objects.select_for_update().get(
            pk=request.query_params.get('other_group_pk'))

        merged_group = ag_models.SubmissionGroup.objects.validate_and_create(
            members=list(group1.members.all()) + list(group2.members.all()))
        tempdir_path = tempfile.mkdtemp()

        for submission in itertools.chain(group1.submissions.all(),
                                          group2.submissions.all()):
            shutil.copytree(
                core_ut.get_submission_dir(submission),
                os.path.join(tempdir_path,
                             core_ut.get_submission_dir_basename(submission)))

            submission.submission_group = merged_group
            submission.save()

        # TODO: move tempdir to direction, consider how to handle save
        #       making stuff on the file system.

        group1.delete()
        group2.delete()

