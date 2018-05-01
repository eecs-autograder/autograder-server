import itertools

from django.contrib.auth.models import User
from django.db import transaction
from drf_composable_permissions.p import P
from drf_yasg.openapi import Schema, Response
from drf_yasg.utils import swagger_auto_schema
from rest_framework import exceptions, mixins, permissions, response, status, viewsets
from rest_framework.decorators import detail_route

import autograder.core.models as ag_models
import autograder.rest_api.permissions as ag_permissions
import autograder.rest_api.serializers as ag_serializers
import autograder.utils.testing as test_ut
from autograder import utils
from autograder.rest_api.views.ag_model_views import (
    ListCreateNestedModelViewSet, AGModelGenericViewSet)
from autograder.rest_api.views.schema_generation import AGModelSchemaBuilder


class CanSendInvitation:
    def has_object_permission(self, request, view, project: ag_models.Project):
        if (project.disallow_group_registration and
                not project.course.is_staff(request.user)):
            return False

        if (project.course.is_handgrader(request.user) and
                not project.course.is_student(request.user) and
                not project.course.is_staff(request.user)):
            return False

        return True


list_create_invitation_permissions = (
    # Only staff can list invitations.
    (P(ag_permissions.IsReadOnly)) & P(ag_permissions.is_staff()) |
    (~P(ag_permissions.IsReadOnly) & P(ag_permissions.can_view_project()) & P(CanSendInvitation))
)


class ListCreateGroupInvitationViewSet(ListCreateNestedModelViewSet):
    serializer_class = ag_serializers.SubmissionGroupInvitationSerializer
    permission_classes = (list_create_invitation_permissions,)

    model_manager = ag_models.Project.objects
    to_one_field_name = 'project'
    reverse_to_one_field_name = 'group_invitations'

    @transaction.atomic()
    def create(self, *args, **kwargs):
        for key in self.request.data:
            if key != 'invited_usernames':
                raise exceptions.ValidationError({'invalid_fields': [key]})

        invited_users = [
            User.objects.get_or_create(username=username)[0]
            for username in self.request.data.pop('invited_usernames')]

        utils.lock_users(itertools.chain([self.request.user], invited_users))

        self.request.data['invitation_creator'] = self.request.user
        self.request.data['invited_users'] = invited_users
        return super().create(self.request, *args, **kwargs)


class CanReadOrEditInvitation(permissions.BasePermission):
    def has_object_permission(self, request, view, invitation):
        is_staff = invitation.project.course.is_staff(request.user)
        is_involved = (request.user == invitation.invitation_creator or
                       request.user in invitation.invited_users.all())

        if request.method.lower() == 'get':
            return is_staff or is_involved

        if invitation.project.disallow_group_registration and not is_staff:
            return False

        return is_involved


invitation_detail_permissions = (
    P(ag_permissions.can_view_project()) & P(CanReadOrEditInvitation)
)


class GroupInvitationDetailViewSet(mixins.RetrieveModelMixin,
                                   mixins.DestroyModelMixin,
                                   AGModelGenericViewSet):
    serializer_class = ag_serializers.SubmissionGroupInvitationSerializer
    permission_classes = (invitation_detail_permissions,)

    model_manager = ag_models.GroupInvitation.objects

    @swagger_auto_schema(
        responses={
            '200': Response(
                schema=AGModelSchemaBuilder.get().get_schema(ag_models.GroupInvitation),
                description='You have accepted the invitation.'),
            '201': Response(
                schema=AGModelSchemaBuilder.get().get_schema(ag_models.Group),
                description='All invited users have accepted the invitation.'
            )
        }

    )
    @transaction.atomic()
    @detail_route(methods=['POST'])
    def accept(self, request, *args, **kwargs):
        """
        Accept this group invitation. If all invitees have accepted,
        create a group, delete the invitation, and return the group.
        """
        invitation = self.get_object()
        invitation.invitee_accept(request.user)
        if not invitation.all_invitees_accepted:
            return response.Response(invitation.to_dict())

        members = ([invitation.invitation_creator] +
                   list(invitation.invited_users.all()))
        utils.lock_users(members)
        # Keep this hook just after the users are locked
        test_ut.mocking_hook()

        serializer = ag_serializers.SubmissionGroupSerializer(
            data={'members': members, 'project': invitation.project})
        serializer.is_valid()
        serializer.save()

        invitation.delete()
        return response.Response(serializer.data,
                                 status=status.HTTP_201_CREATED)

    @transaction.atomic()
    def destroy(self, request, *args, **kwargs):
        """
        Revoke or reject this invitation.
        """
        invitation = self.get_object()
        message = (
            "{} has rejected {}'s invitation to work together "
            "for project '{}'. The invitation has been deleted, "
            "and no groups have been created".format(
                request.user, invitation.invitation_creator.username,
                invitation.project.name))
        for user in itertools.chain([invitation.invitation_creator],
                                    invitation.invited_users.all()):
            ag_models.Notification.objects.validate_and_create(
                message=message, recipient=user)

        invitation.delete()
        return response.Response(status=status.HTTP_204_NO_CONTENT)
