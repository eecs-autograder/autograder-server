from django.contrib.auth.models import User
from django import http
from .endpoint_base import EndpointBase
from django.core.urlresolvers import reverse
from django.core import exceptions

from autograder.core import models as ag_models
from autograder.rest_api import url_shortcuts


class GetCurrentUserEndpoint(EndpointBase):
    def get(self, request, *args, **kwargs):
        user = request.user

        response = {
            "type": "user",
            "id": user.pk,
            "username": user.username,
            "urls": {
                "self": reverse('user:get', kwargs={'pk': user.pk}),
                "courses_is_admin_for": reverse(
                    'user:admin-courses', kwargs={'pk': user.pk}),
                "semesters_is_staff_for": reverse(
                    'user:staff-semesters', kwargs={'pk': user.pk}),
                "semesters_is_enrolled_in": reverse(
                    'user:enrolled-semesters', kwargs={'pk': user.pk}),
                "groups_is_member_of": reverse(
                    'user:submission-groups', kwargs={'pk': user.pk}),

                "group_invitations_sent": reverse(
                    'user:invitations-sent', kwargs={'pk': user.pk}),
                "group_invitations_received": reverse(
                    'user:invitations-received', kwargs={'pk': user.pk}),

                "notifications": reverse(
                    'user:notifications', kwargs={'pk': user.pk})
            }
        }

        return http.JsonResponse(response)


class GetUser(EndpointBase):
    def get(self, request, pk, *args, **kwargs):
        pk = int(pk)
        user = request.user

        if pk != user.pk:
            raise exceptions.PermissionDenied()

        response = {
            "type": "user",
            "id": user.pk,
            "username": user.username,
            "urls": {
                "self": reverse('user:get', kwargs={'pk': user.pk}),
                "courses_is_admin_for": reverse(
                    'user:admin-courses', kwargs={'pk': user.pk}),
                "semesters_is_staff_for": reverse(
                    'user:staff-semesters', kwargs={'pk': user.pk}),
                "semesters_is_enrolled_in": reverse(
                    'user:enrolled-semesters', kwargs={'pk': user.pk}),
                "groups_is_member_of": reverse(
                    'user:submission-groups', kwargs={'pk': user.pk}),

                "group_invitations_sent": reverse(
                    'user:invitations-sent', kwargs={'pk': user.pk}),
                "group_invitations_received": reverse(
                    'user:invitations-received', kwargs={'pk': user.pk}),

                "notifications": reverse(
                    'user:notifications', kwargs={'pk': user.pk})
            }
        }

        return http.JsonResponse(response)


class GetUserCoursesIsAdminForEndpoint(EndpointBase):
    def get(self, request, pk, *args, **kwargs):
        pk = int(pk)
        user = request.user

        if pk != user.pk:
            raise exceptions.PermissionDenied()

        response = {
            "courses": [
                {
                    "name": course.name,
                    "url": url_shortcuts.course_url(course)
                }
                for course in user.courses_is_admin_for.all()
            ]
        }

        return http.JsonResponse(response)


class GetUserSemstersIsStaffForEndpoint(EndpointBase):
    def get(self, request, pk, *args, **kwargs):
        pk = int(pk)
        user = request.user

        if pk != user.pk:
            raise exceptions.PermissionDenied()

        response = {
            "semesters": [
                {
                    "name": semester.name,
                    'course_name': semester.course.name,
                    "url": url_shortcuts.semester_url(semester)
                }
                for semester in
                ag_models.Semester.get_staff_semesters_for_user(user)
            ]
        }

        return http.JsonResponse(response)


class GetUserSemestersIsEnrolledInEndpoint(EndpointBase):
    def get(self, request, pk, *args, **kwargs):
        pk = int(pk)
        user = request.user

        if pk != user.pk:
            raise exceptions.PermissionDenied()

        response = {
            "semesters": [
                {
                    "name": semester.name,
                    'course_name': semester.course.name,
                    "url": url_shortcuts.semester_url(semester)
                }
                for semester in user.semesters_is_enrolled_in.all()
            ]
        }

        return http.JsonResponse(response)


class GetUserGroupsIsMemberOfEndpoint(EndpointBase):
    def get(self, request, pk, *args, **kwargs):
        pk = int(pk)
        user = request.user

        if pk != user.pk:
            raise exceptions.PermissionDenied()

        response = {
            "groups": [
                {
                    "project_name": group.project.name,
                    'semester_name': group.project.semester.name,
                    'course_name': group.project.semester.course.name,
                    "url": url_shortcuts.group_url(group)
                }
                for group in user.groups_is_member_of.all()
            ]
        }

        return http.JsonResponse(response)


class GetGroupInvitationsSentEndpoint(EndpointBase):
    def get(self, request, pk, *args, **kwargs):
        pk = int(pk)
        user = request.user

        if pk != user.pk:
            raise exceptions.PermissionDenied()

        response = {
            "group_requests": [
                {
                    "project_name": invitation.project.name,
                    "request_sender": invitation.invitation_creator.username,
                    "url": url_shortcuts.invitation_url(invitation)
                }
                for invitation in user.group_invitations_sent.all()
            ]
        }

        return http.JsonResponse(response)


class GetGroupInvitationsReceivedEndpoint(EndpointBase):
    def get(self, request, pk, *args, **kwargs):
        pk = int(pk)
        user = request.user

        if pk != user.pk:
            raise exceptions.PermissionDenied()

        response = {
            "group_requests": [
                {
                    "project_name": invitation.project.name,
                    "request_sender": invitation.invitation_creator.username,
                    "url": url_shortcuts.invitation_url(invitation)
                }
                for invitation in user.group_invitations_received.all()
            ]
        }

        return http.JsonResponse(response)


class GetUserNotificationsEndpoint(EndpointBase):
    def get(self, request, pk, *args, **kwargs):
        pk = int(pk)
        user = request.user

        if pk != user.pk:
            raise exceptions.PermissionDenied()

        response = {
            "notifications": [
                {
                    "timestamp": notification.timestamp,
                    "url": url_shortcuts.notification_url(notification)
                }
                for notification in user.notifications.all()
            ]
        }

        return http.JsonResponse(response)

# -----------------------------------------------------------------------------
# -----------------------------------------------------------------------------


class GetUserNotificationEndpoint(EndpointBase):
    def get(self, request, pk, *args, **kwargs):
        pk = int(pk)
        notification = ag_models.Notification.objects.get(pk=pk)

        if notification.recipient != request.user:
            raise exceptions.PermissionDenied()

        response = {
            "type": "notification",
            "id": notification.pk,
            "timestamp": notification.timestamp,
            "message": notification.message,

            "urls": {
                "self": url_shortcuts.notification_url(notification),
                "user": url_shortcuts.user_url(request.user)
            }
        }

        return http.JsonResponse(response)
