import itertools
import os
import json

from django.utils import timezone
from django import http
from django.core import exceptions
from django.contrib.auth.models import User

from django.db import transaction

from .endpoint_base import EndpointBase

from autograder.core import models as ag_models
from autograder.rest_api import url_shortcuts

from .utilities import check_can_view_project, check_can_view_group

import autograder.core.shared.feedback_configuration as fbc


class GetRejectSubmissionGroupInvitationEndpoint(EndpointBase):
    def get(self, request, pk, *args, **kwargs):
        pk = int(pk)
        invitation = ag_models.SubmissionGroupInvitation.objects.get(pk=pk)

        check_can_view_project(request.user, invitation.project)
        _check_is_involved_in_invitation(request.user, invitation)

        response = {
            "type": "submission_group_invitation",
            "id": invitation.pk,
            "invitation_creator": invitation.invitation_creator.username,
            "invited_members_to_acceptance": {
                user.username: (
                    user.username in invitation.invitees_who_accepted)
                for user in invitation.invited_users.all()
            },
            "semester_name": invitation.project.semester.name,
            "project_name": invitation.project.name,
            "urls": {
                "self": url_shortcuts.invitation_url(invitation),
                "accept": url_shortcuts.invitation_accept_url(invitation),
                "project": url_shortcuts.project_url(invitation.project)
            }
        }

        return http.JsonResponse(response)

    def delete(self, request, pk, *args, **kwargs):
        pk = int(pk)
        with transaction.atomic():
            invitation = (ag_models.SubmissionGroupInvitation.objects.
                          select_for_update().get(pk=pk))

            check_can_view_project(request.user, invitation.project)
            _check_is_involved_in_invitation(request.user, invitation)

            if request.user == invitation.invitation_creator:
                for user in invitation.invited_users.all():
                    user.notifications.create(
                        message='{} revoked their group invitation for '
                                '{} - {} - {}'.format(
                                    invitation.invitation_creator.username,
                                    invitation.project.semester.course.name,
                                    invitation.project.semester.name,
                                    invitation.project.name))
            else:
                users_to_notify = itertools.chain(
                    (invitation.invitation_creator,),
                    invitation.invited_users.exclude(pk=request.user.pk))
                for user in users_to_notify:
                    user.notifications.create(
                        message="{} rejected {}'s group invitation for "
                                "{} - {} - {}".format(
                                    request.user.username,
                                    invitation.invitation_creator.username,
                                    invitation.project.semester.course.name,
                                    invitation.project.semester.name,
                                    invitation.project.name))

            invitation.delete()

        return http.HttpResponse(status=204)


class AcceptSubmissionGroupInvitationEndpoint(EndpointBase):
    def post(self, request, pk, *args, **kwargs):
        pk = int(pk)
        with transaction.atomic():
            invitation = (ag_models.SubmissionGroupInvitation.objects.
                          select_for_update().get(pk=pk))

            check_can_view_project(request.user, invitation.project)
            _check_is_involved_in_invitation(request.user, invitation)

            invitation.invitee_accept(request.user.username)

            users_to_notify = itertools.chain(
                [invitation.invitation_creator],
                invitation.invited_users.exclude(pk=request.user.pk))
            for user in users_to_notify:
                user.notifications.create(
                    message="{} accepted {}'s group invitation for "
                            "{} - {} - {}".format(
                                request.user.username,
                                invitation.invitation_creator.username,
                                invitation.project.semester.course.name,
                                invitation.project.semester.name,
                                invitation.project.name))

            if not invitation.all_invitees_accepted:
                return http.HttpResponse(status=204)

            for user in itertools.chain(
                    [invitation.invitation_creator],
                    invitation.invited_users.all()):
                user.group_invitations_sent.all().delete()
                user.group_invitations_received.all().delete()

            group = ag_models.SubmissionGroup.objects.validate_and_create(
                members=([invitation.invitation_creator.username] +
                         list(invitation.invitees_who_accepted)),
                project=invitation.project)

            invitation.delete()

            return http.HttpResponse(
                url_shortcuts.group_url(group), status=201)

# -----------------------------------------------------------------------------


def _check_is_involved_in_invitation(user, invitation):
    if invitation.invitation_creator == user:
        return

    if user in invitation.invited_users.all():
        return

    raise exceptions.PermissionDenied()
