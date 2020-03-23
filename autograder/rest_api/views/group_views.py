import itertools
import os
import shutil
import tempfile

from django.contrib.auth.models import User
from django.db import transaction
from django.db.models import Prefetch
from django.utils import timezone
from django.utils.decorators import method_decorator
from drf_composable_permissions.p import P
# from drf_yasg.openapi import Parameter
# from drf_yasg.utils import swagger_auto_schema
from rest_framework import decorators, mixins, permissions, response, status

import autograder.core.models as ag_models
import autograder.core.utils as core_ut
import autograder.rest_api.serializers as ag_serializers
import autograder.utils.testing as test_ut
from autograder import utils
from autograder.core.models.get_ultimate_submissions import get_ultimate_submission
from autograder.rest_api import permissions as ag_permissions, transaction_mixins
from autograder.rest_api.views.ag_model_views import (
    AGModelGenericViewSet,
    ListCreateNestedModelViewSet, require_query_params, require_body_params)
from autograder.rest_api.views.schema_generation import APITags


class GroupsViewSet(ListCreateNestedModelViewSet):
    serializer_class = ag_serializers.SubmissionGroupSerializer
    permission_classes = (
        P(ag_permissions.is_admin())
        | ((P(ag_permissions.is_staff()) | P(ag_permissions.is_handgrader()))
            & ag_permissions.IsReadOnly),
    )

    pk_key = 'project_pk'
    model_manager = ag_models.Project.objects.select_related('course')
    to_one_field_name = 'project'
    reverse_to_one_field_name = 'groups'

    def get_queryset(self):
        queryset = super().get_queryset()
        if self.request.method.lower() == 'get':
            queryset = queryset.prefetch_related(
                Prefetch('submissions',
                         ag_models.Submission.objects.defer('denormalized_ag_test_results'))
            )

        return queryset

    # @swagger_auto_schema(
    #     request_body_parameters=[
    #         Parameter(name='member_names', in_='body',
    #                   description='Usernames to add to the new Group.',
    #                   type='List[string]', required=True)]
    # )
    @transaction.atomic()
    @method_decorator(require_body_params('member_names'))
    def create(self, request, *args, **kwargs):
        project = self.get_object()
        request.data['project'] = project

        users = [
            User.objects.get_or_create(username=username)[0]
            for username in request.data.pop('member_names')]

        utils.lock_users(users)
        # Keep this hook immediately after locking the users.
        test_ut.mocking_hook()

        request.data['members'] = users
        request.data['check_group_size_limits'] = (
            not project.course.is_admin(request.user))

        return super().create(request, *args, **kwargs)


class _CanCreateSoloGroup(permissions.BasePermission):
    def has_object_permission(self, request, view, project):
        if project.course.is_staff(request.user):
            return True

        if not project.visible_to_students:
            return False

        return (project.course.is_student(request.user)
                or project.guests_can_submit)


class CreateSoloGroupView(mixins.CreateModelMixin, AGModelGenericViewSet):
    permission_classes = (_CanCreateSoloGroup,)
    serializer_class = ag_serializers.SubmissionGroupSerializer

    pk_key = 'project_pk'
    model_manager = ag_models.Project.objects.select_related('course')

    api_tags = [APITags.groups]

    # @swagger_auto_schema(request_body_parameters=[])
    @transaction.atomic()
    def create(self, request, *args, **kwargs):
        """
        Creates a group containing only the user making the request.
        """
        project = self.get_object()

        utils.lock_users([request.user])

        data = {
            'project': project,
            'members': [request.user],
            'check_group_size_limits': (
                not project.course.is_staff(request.user))
        }
        serializer = self.get_serializer(data=data)
        serializer.is_valid()
        serializer.save()

        return response.Response(serializer.data, status=status.HTTP_201_CREATED)


is_staff_or_member = ag_permissions.is_staff_or_group_member()
can_view_project = ag_permissions.can_view_project(lambda group: group.project)
group_permissions = (P(ag_permissions.is_admin())
                     | (P(ag_permissions.IsReadOnly) & can_view_project & is_staff_or_member))


class _UltimateSubmissionPermissions(permissions.BasePermission):
    def has_object_permission(self, request, view, group):
        project = group.project
        course = group.project.course
        is_staff = course.is_staff(request.user)

        # Staff and higher can always view their own ultimate submission
        if is_staff and group.members.filter(pk=request.user.pk).exists():
            return True

        return (ag_permissions.deadline_is_past(group, request.user)
                and not project.hide_ultimate_submission_fdbk)


class GroupDetailViewSet(mixins.RetrieveModelMixin,
                         transaction_mixins.TransactionPartialUpdateMixin,
                         AGModelGenericViewSet):
    serializer_class = ag_serializers.SubmissionGroupSerializer
    permission_classes = (group_permissions,)

    model_manager = ag_models.Group.objects.select_related(
        'project__course').prefetch_related('members', 'submissions')

    # @swagger_auto_schema(
    #     extra_request_body_parameters=[
    #         Parameter(name='member_names', in_='body',
    #                   description='Usernames to replace the current group members with.',
    #                   type='List[string]')]
    # )
    @transaction.atomic()
    def partial_update(self, request, *args, **kwargs):
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
        return super().partial_update(request, *args, **kwargs)

    @transaction.atomic
    def delete(self, request, *args, **kwargs):
        """
        "Deletes" a group by removing all of its members. Each group
        member is replaced with a dummy user whose username contains
        the group's pk and the original username. This allows "deleted"
        groups to be easily viewable and recoverable by the user.
        """
        group = self.get_object()
        new_members = []
        for username in group.member_names:
            new_username = f'~deleted_{group.pk}_{username}'
            new_members.append(User.objects.get_or_create(username=new_username)[0])

        group.validate_and_update(
            members=new_members, check_group_size_limits=False, ignore_guest_restrictions=True)

        return response.Response(status=status.HTTP_204_NO_CONTENT)

    # @swagger_auto_schema(
    #     api_tags=[APITags.groups, APITags.submissions],
    #     responses={'200': ag_serializers.SubmissionSerializer}
    # )
    @decorators.action(
        detail=True,
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
        ultimate_submission = get_ultimate_submission(group, user=request.user)
        if ultimate_submission is None:
            return response.Response(status=status.HTTP_404_NOT_FOUND)

        return response.Response(ag_serializers.SubmissionSerializer(ultimate_submission).data)

    # @swagger_auto_schema(
    #     manual_parameters=[
    #         Parameter(name='other_group_pk', in_='query',
    #                   type='int', required=True,
    #                   description='The ID of the second group to merge.')
    #     ],
    #     request_body_parameters=[]
    # )
    @method_decorator(require_query_params('other_group_pk'))
    @decorators.action(detail=True, methods=['POST'])
    @transaction.atomic()
    def merge_with(self, request, *args, **kwargs):
        """
        Merge two groups together, preserving their submissions, and
        return the newly created group.
        """
        other_group_pk = request.query_params.get('other_group_pk')

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

            submission.group = merged_group
            submission.save()

        merged_group_dir = core_ut.get_student_group_dir(merged_group)
        shutil.rmtree(merged_group_dir)
        shutil.move(tempdir_path, merged_group_dir)

    def _get_merged_extended_due_date(self, group1, group2):
        if group1.extended_due_date is None:
            return group2.extended_due_date
        if group2.extended_due_date is None:
            return group1.extended_due_date

        return max(group1.extended_due_date, group2.extended_due_date)
