from django.contrib.auth.models import User
from django import http
from .request_handler_base import RequestHandlerBase
from django.core.urlresolvers import reverse


class GetUser(RequestHandlerBase):
    def get(self, request, pk, *args, **kwargs):
        user = User.objects.get(pk=pk)
        response_content = {
            "type": "user",
            "id": user.pk,
            "username": user.username,
            "urls": {
                "self": reverse('user:get', kwargs={'pk': user.pk})
            }
        }

        if user.pk != request.user.pk:
            return http.JsonResponse(response_content)

        response_content['urls'].update({
            "courses_is_admin_for": reverse(
                'user:admin-courses', kwargs={'pk': user.pk}),
            "semesters_is_staff_for": reverse(
                'user:staff-semesters', kwargs={'pk': user.pk}),
            "semesters_is_enrolled_in": reverse(
                'user:enrolled-semesters', kwargs={'pk': user.pk}),
            "groups_is_member_of": reverse(
                'user:submission-groups', kwargs={'pk': user.pk}),

            "pending_group_requests": reverse(
                'user:pending-group-requests', kwargs={'pk': user.pk}),

            "notifications": reverse(
                'user:notifications', kwargs={'pk': user.pk})
        })

        return http.JsonResponse(response_content)


class GetUserCoursesIsAdminFor(RequestHandlerBase):
    pass


class GetUserSemstersIsStaffFor(RequestHandlerBase):
    pass


class GetUserSemestersIsEnrolledIn(RequestHandlerBase):
    pass


class GetUserGroupsIsMemberOf(RequestHandlerBase):
    pass


class GetUserPendingGroupRequests(RequestHandlerBase):
    pass


class GetUserNotifications(RequestHandlerBase):
    pass
