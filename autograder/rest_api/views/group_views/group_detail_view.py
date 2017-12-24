import tempfile
import os
import shutil
import itertools

from django.contrib.auth.models import User
from django.utils import timezone
from django.db import transaction

from rest_framework import mixins, permissions, decorators, response, status

from drf_composable_permissions.p import P

import autograder.core.models as ag_models
from autograder.core.models.get_ultimate_submissions import get_ultimate_submission
import autograder.rest_api.serializers as ag_serializers
from autograder.rest_api import transaction_mixins

from autograder import utils
import autograder.utils.testing as test_ut
import autograder.core.utils as core_ut
from autograder.rest_api.views.ag_model_views import AGModelGenericViewSet

import autograder.rest_api.permissions as ag_permissions


is_admin = ag_permissions.is_admin(lambda group: group.project.course)
is_staff_or_member = ag_permissions.is_staff_or_group_member()
can_view_project = ag_permissions.can_view_project(lambda group: group.project)
group_permissions = (P(is_admin) |
                     (P(ag_permissions.IsReadOnly) & can_view_project & is_staff_or_member))


class _UltimateSubmissionPermissions(permissions.BasePermission):
    def has_object_permission(self, request, view, group):
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


class GroupDetailViewSet(mixins.RetrieveModelMixin,
                         transaction_mixins.TransactionUpdateMixin,
                         AGModelGenericViewSet):
    serializer_class = ag_serializers.SubmissionGroupSerializer
    permission_classes = (group_permissions,)

    model_manager = ag_models.SubmissionGroup.objects.select_related(
        'project__course').prefetch_related('members')

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

    @decorators.detail_route(
        permission_classes=(group_permissions, _UltimateSubmissionPermissions,))
    def ultimate_submission(self, request, *args, **kwargs):
        """
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
        """
        group = self.get_object()
        ultimate_submission = get_ultimate_submission(group.project, group.pk)
        if ultimate_submission is None:
            return response.Response(status=status.HTTP_404_NOT_FOUND)

        return response.Response(ag_serializers.SubmissionSerializer(ultimate_submission).data)

    @decorators.detail_route(methods=['POST'])
    @transaction.atomic()
    def merge_with(self, request, *args, **kwargs):
        other_group_pk = request.query_params.get('other_group_pk')

        if other_group_pk is None:
            return response.Response(
                data={'other_group_pk': 'Missing required query param: other_group_pk'},
                status=status.HTTP_400_BAD_REQUEST)

        group1 = self.get_object()
        group2 = self.get_object(pk_override=other_group_pk)

        if group1.project != group2.project:
            return response.Response(
                data={'groups': 'Cannot merge groups from different projects'},
                status=status.HTTP_400_BAD_REQUEST
            )

        merged_members = list(group1.members.all()) + list(group2.members.all())
        project = group1.project

        # Can't have duplicate members between groups in a project,
        # but still need to copy submissions before they get
        # cascade-deleted
        group1.members.clear()
        group2.members.clear()

        merged_group_serializer = ag_serializers.SubmissionGroupSerializer(
            data={'members': merged_members,
                  'project': project,
                  'extended_due_date': self._get_merged_extended_due_date(group1, group2),
                  'check_group_size_limits': False})
        merged_group_serializer.is_valid()
        merged_group_serializer.save()
        merged_group = merged_group_serializer.instance

        self._merge_group_files(group1=group1, group2=group2, merged_group=merged_group)

        group1.delete()
        group2.delete()

        content = ag_serializers.SubmissionGroupSerializer(merged_group).data
        return response.Response(content, status=status.HTTP_201_CREATED)

    def _merge_group_files(self, group1, group2, merged_group):
        tempdir_path = tempfile.mkdtemp()

        for submission in itertools.chain(group1.submissions.all(),
                                          group2.submissions.all()):
            shutil.copytree(
                core_ut.get_submission_dir(submission),
                os.path.join(tempdir_path,
                             core_ut.get_submission_dir_basename(submission)))

            submission.submission_group = merged_group
            submission.save()

        merged_group_dir = core_ut.get_student_submission_group_dir(merged_group)
        shutil.rmtree(merged_group_dir)
        shutil.move(tempdir_path, merged_group_dir)

    def _get_merged_extended_due_date(self, group1, group2):
        if group1.extended_due_date is None:
            return group2.extended_due_date
        if group2.extended_due_date is None:
            return group1.extended_due_date

        return max(group1.extended_due_date, group2.extended_due_date)
