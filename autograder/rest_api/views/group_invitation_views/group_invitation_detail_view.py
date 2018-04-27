import itertools

from django.db import transaction

from rest_framework import viewsets, mixins, permissions, response, status

import autograder.core.models as ag_models
import autograder.rest_api.serializers as ag_serializers

from autograder import utils
import autograder.utils.testing as test_ut

from autograder.rest_api.views.permission_components import user_can_view_project
from autograder.rest_api.views.load_object_mixin import build_load_object_mixin


class _Permissions(permissions.BasePermission):
    def has_object_permission(self, request, view, invitation):
        if not user_can_view_project(request.user, invitation.project):
            return False

        is_staff = invitation.project.course.is_staff(request.user)
        is_involved = (request.user == invitation.invitation_creator or
                       request.user in invitation.invited_users.all())

        if request.method.lower() == 'get':
            return is_staff or is_involved

        if invitation.project.disallow_group_registration and not is_staff:
            return False

        return is_involved


class GroupInvitationDetailViewSet(
        build_load_object_mixin(ag_models.GroupInvitation),
        mixins.RetrieveModelMixin,
        viewsets.GenericViewSet):
    queryset = ag_models.GroupInvitation.objects.all()
    serializer_class = ag_serializers.SubmissionGroupInvitationSerializer
    permission_classes = (permissions.IsAuthenticated, _Permissions)

    @transaction.atomic()
    def post(self, request, pk, *args, **kwargs):
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
        return response.Response(
            serializer.data, status=status.HTTP_201_CREATED,
            headers=mixins.CreateModelMixin.get_success_headers(
                self, serializer.data))

    @transaction.atomic()
    def delete(self, request, pk, *args, **kwargs):
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
