import itertools

from django.core.urlresolvers import reverse

from rest_framework.test import APIClient

import autograder.rest_api.serializers as ag_serializers

from autograder.utils.testing import UnitTestBase
import autograder.rest_api.tests.test_views.common_generic_data as test_data
import autograder.rest_api.tests.test_views.common_test_impls as test_impls


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
        for user in self.all_users:
            self.do_list_objects_test(
                self.client, user, user_url(user, 'user-courses-is-admin-for'),
                ag_serializers.CourseSerializer(
                    user.courses_is_admin_for.all(), many=True).data)

    def test_other_list_courses_is_admin_for_forbidden(self):
        self.do_get_user_info_permission_denied_test(
            'user-courses-is-admin-for')

    def test_self_list_courses_is_staff_for(self):
        for user in self.all_users:
            self.do_list_objects_test(
                self.client, user, user_url(user, 'user-courses-is-staff-for'),
                ag_serializers.CourseSerializer(
                    user.courses_is_staff_for.all(), many=True).data)

    def test_other_list_courses_is_staff_for_forbidden(self):
        self.do_get_user_info_permission_denied_test(
            'user-courses-is-staff-for')

    def test_self_list_courses_is_enrolled_in(self):
        for user in self.all_users:
            self.do_list_objects_test(
                self.client, user, user_url(user, 'user-courses-is-enrolled-in'),
                ag_serializers.CourseSerializer(
                    user.courses_is_enrolled_in.all(), many=True).data)

    def test_other_list_courses_is_enrolled_in_forbidden(self):
        self.do_get_user_info_permission_denied_test(
            'user-courses-is-enrolled-in')

    def test_self_list_groups_is_member_of(self):
        for user in self.all_users:
            self.do_list_objects_test(
                self.client, user, user_url(user, 'user-groups-is-member-of'),
                ag_serializers.SubmissionGroupSerializer(
                    user.groups_is_member_of.all(), many=True).data)

    def test_other_list_groups_is_member_of_forbidden(self):
        self.do_get_user_info_permission_denied_test(
            'user-groups-is-member-of')

    def test_self_list_invitations_received(self):
        for user in self.all_users:
            self.do_list_objects_test(
                self.client, user, user_url(user,
                                            'user-group-invitations-received'),
                ag_serializers.SubmissionGroupInvitationSerializer(
                    user.group_invitations_received.all(), many=True).data)

    def test_other_list_invitations_received_forbidden(self):
        self.do_get_user_info_permission_denied_test(
            'user-group-invitations-received')

    def test_self_list_invitations_sent(self):
        for user in self.all_users:
            self.do_list_objects_test(
                self.client, user, user_url(user,
                                            'user-group-invitations-sent'),
                ag_serializers.SubmissionGroupInvitationSerializer(
                    user.group_invitations_sent.all(), many=True).data)

    def test_other_list_invitations_sent_forbidden(self):
        self.do_get_user_info_permission_denied_test(
            'user-group-invitations-sent')

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
