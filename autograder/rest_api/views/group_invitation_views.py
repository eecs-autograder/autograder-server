import itertools

from django.contrib.auth.models import User
from django.db import transaction

from rest_framework import viewsets, mixins, permissions, response, status

import autograder.core.models as ag_models
import autograder.rest_api.serializers as ag_serializers

from .permission_components import user_can_view_project
from .load_object_mixin import build_load_object_mixin


class _Permissions(permissions.BasePermission):
    def has_object_permission(self, request, view, invitation):
        if not user_can_view_project(request.user, invitation.project):
            return False

        if request.user == invitation.invitation_creator:
            return True

        if request.user in invitation.invited_users.all():
            return True

        if request.method.lower() == 'get':
            return invitation.project.course.is_course_staff(request.user)

        return False


class GroupInvitationViewset(
        build_load_object_mixin(ag_models.SubmissionGroupInvitation),
        mixins.RetrieveModelMixin,
        viewsets.GenericViewSet):
    queryset = ag_models.SubmissionGroupInvitation.objects.all()
    serializer_class = ag_serializers.SubmissionGroupInvitationSerializer
    permission_classes = (permissions.IsAuthenticated, _Permissions)

    @transaction.atomic()
    def post(self, request, pk, *args, **kwargs):
        invitation = self.get_object()
        invitation.invitee_accept(request.user)
        if not invitation.all_invitees_accepted:
            return response.Response(invitation.to_dict())

        locked_creator = User.objects.select_for_update().get(
            pk=invitation.invitation_creator.pk)
        members = ([locked_creator] +
                   list(invitation.invited_users.select_for_update().all()))
        group = ag_models.SubmissionGroup.objects.validate_and_create(
            members, project=invitation.project)
        invitation.delete()
        return response.Response(group.to_dict(),
                                 status=status.HTTP_201_CREATED)

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
