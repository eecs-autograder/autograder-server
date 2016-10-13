import itertools

from django.core.urlresolvers import reverse

from rest_framework.test import APIClient

import autograder.core.models as ag_models
import autograder.rest_api.serializers as ag_serializers

from autograder.utils.testing import UnitTestBase
import autograder.rest_api.tests.test_views.common_generic_data as test_data
import autograder.rest_api.tests.test_views.common_test_impls as test_impls

import autograder.utils.testing.model_obj_builders as obj_build


class RetrieveUserTestCase(test_data.Client,
                           test_data.Project,
                           test_data.Group,
                           test_impls.GetObjectTest,
                           UnitTestBase):
    def test_self_get_currently_authenticated_user(self):
        for user in self.all_users:
            self.do_get_object_test(self.client, user, reverse('user-current'),
                                    ag_serializers.UserSerializer(user).data)

    def test_self_get_user(self):
        for user in self.all_users:
            self.do_get_object_test(self.client, user, user_url(user),
                                    ag_serializers.UserSerializer(user).data)

    def test_other_get_user_permission_denied(self):
        self.do_get_user_info_permission_denied_test('user-detail')

    def test_self_list_courses_is_admin_for(self):
        self.do_list_objects_test(
            self.client, self.admin,
            user_url(self.admin, 'user-courses-is-admin-for'),
            ag_serializers.CourseSerializer([self.course], many=True).data)

        for user in self.staff, self.enrolled, self.nobody:
            self.do_list_objects_test(
                self.client, user,
                user_url(user, 'user-courses-is-admin-for'),
                ag_serializers.CourseSerializer([], many=True).data)

    def test_other_list_courses_is_admin_for_forbidden(self):
        self.do_get_user_info_permission_denied_test(
            'user-courses-is-admin-for')

    def test_self_list_courses_is_staff_for(self):
        self.do_list_objects_test(
            self.client, self.staff, user_url(self.staff, 'user-courses-is-staff-for'),
            ag_serializers.CourseSerializer([self.course], many=True).data)

        # Note: Even though admins have staff privileges, they are not
        # listed here with other staff members.
        for user in self.admin, self.enrolled, self.nobody:
            self.do_list_objects_test(
                self.client, user, user_url(user, 'user-courses-is-staff-for'),
                ag_serializers.CourseSerializer([], many=True).data)

    def test_other_list_courses_is_staff_for_forbidden(self):
        self.do_get_user_info_permission_denied_test(
            'user-courses-is-staff-for')

    def test_self_list_courses_is_enrolled_in(self):
        self.do_list_objects_test(
            self.client, self.enrolled,
            user_url(self.enrolled, 'user-courses-is-enrolled-in'),
            ag_serializers.CourseSerializer(
                self.enrolled.courses_is_enrolled_in.all(), many=True).data)

        for user in self.admin, self.staff, self.nobody:
            self.do_list_objects_test(
                self.client, user, user_url(user, 'user-courses-is-enrolled-in'),
                ag_serializers.CourseSerializer([], many=True).data)

    def test_other_list_courses_is_enrolled_in_forbidden(self):
        self.do_get_user_info_permission_denied_test(
            'user-courses-is-enrolled-in')

    def test_self_list_groups_is_member_of(self):
        for group in self.all_groups(self.visible_public_project):
            self.do_list_objects_test(
                self.client, group.members.first(),
                user_url(group.members.first(), 'user-groups-is-member-of'),
                ag_serializers.SubmissionGroupSerializer(
                    [group], many=True).data)

        other_user = obj_build.create_dummy_user()
        self.do_list_objects_test(
            self.client, other_user,
            user_url(other_user, 'user-groups-is-member-of'),
            ag_serializers.SubmissionGroupSerializer([], many=True).data)

    def test_other_list_groups_is_member_of_forbidden(self):
        self.do_get_user_info_permission_denied_test(
            'user-groups-is-member-of')

    def test_self_list_invitations_received(self):
        invite = self.non_enrolled_group_invitation(self.visible_public_project)
        for user in invite.invited_users.all():
            self.do_list_objects_test(
                self.client, user,
                user_url(user, 'user-group-invitations-received'),
                ag_serializers.SubmissionGroupInvitationSerializer(
                    [invite], many=True).data)

        other_user = obj_build.create_dummy_user()
        self.do_list_objects_test(
            self.client, other_user,
            user_url(other_user, 'user-group-invitations-received'),
            ag_serializers.SubmissionGroupInvitationSerializer([], many=True).data)

    def test_other_list_invitations_received_forbidden(self):
        self.do_get_user_info_permission_denied_test(
            'user-group-invitations-received')

    def test_self_list_invitations_sent(self):
        invite = self.non_enrolled_group_invitation(self.visible_public_project)
        self.do_list_objects_test(
            self.client, invite.invitation_creator,
            user_url(invite.invitation_creator, 'user-group-invitations-sent'),
            ag_serializers.SubmissionGroupInvitationSerializer(
                [invite], many=True).data)

        other_user = obj_build.create_dummy_user()
        self.do_list_objects_test(
            self.client, other_user,
            user_url(other_user, 'user-group-invitations-sent'),
            ag_serializers.SubmissionGroupInvitationSerializer([], many=True).data)

    def test_other_list_invitations_sent_forbidden(self):
        self.do_get_user_info_permission_denied_test(
            'user-group-invitations-sent')

    def test_self_list_notifications(self):
        for user in self.all_users:
            self.do_list_objects_test(
                self.client, user,
                user_url(user, 'user-notifications'),
                ag_serializers.NotificationSerializer([], many=True).data)

            notification = ag_models.Notification.objects.validate_and_create(
                message='Hai there', recipient=user)
            self.do_list_objects_test(
                self.client, user,
                user_url(user, 'user-notifications'),
                ag_serializers.NotificationSerializer([notification], many=True).data)

    def test_other_list_notifications_permission_denied(self):
        self.do_get_user_info_permission_denied_test('user-notifications')

    def do_get_user_info_permission_denied_test(self, url_lookup):
        for requester, to_get in itertools.product(self.all_users,
                                                   self.all_users):
            if requester == to_get:
                continue

            self.do_permission_denied_get_test(
                self.client, requester, user_url(to_get, url_lookup))

    @property
    def all_users(self):
        return [self.admin, self.staff, self.enrolled, self.nobody]


def user_url(user, lookup='user-detail'):
    return reverse(lookup, kwargs={'pk': user.pk})
