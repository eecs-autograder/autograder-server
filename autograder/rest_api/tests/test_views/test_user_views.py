from django.contrib.auth.models import Permission, User
from django.urls import reverse
from rest_framework import status
from rest_framework.authtoken.models import Token
from rest_framework.test import APIClient

import autograder.core.models as ag_models
import autograder.utils.testing.model_obj_builders as obj_build
from autograder.rest_api.serialize_user import serialize_user
from autograder.rest_api.tests.test_views.ag_view_test_base import AGViewTestBase
from autograder.utils.testing import UnitTestBase


class GetUserTestCase(AGViewTestBase):
    def setUp(self):
        super().setUp()
        self.client = APIClient()
        self.user = obj_build.make_user()

    def test_self_get_currently_authenticated_user(self):
        self.do_get_object_test(
            self.client, self.user, reverse('current-user'), serialize_user(self.user))

    def test_self_get_user(self):
        self.do_get_object_test(
            self.client, self.user, user_url(self.user), serialize_user(self.user))

    def test_other_get_user_permission_denied(self):
        other_user = obj_build.make_user()
        self.do_permission_denied_get_test(self.client, other_user, user_url(self.user))


class RevokeCurrentUserAPIToken(AGViewTestBase):
    def setUp(self):
        super().setUp()
        self.client = APIClient()
        self.user = obj_build.make_user()

    def test_revoke_current_user_api_token(self) -> None:
        Token.objects.create(user=self.user)
        self.assertTrue(Token.objects.filter(user=self.user).exists())

        self.client.force_authenticate(self.user)
        response = self.client.delete(reverse('revoke-api-token'))
        self.assertEqual(status.HTTP_204_NO_CONTENT, response.status_code)
        self.assertFalse(Token.objects.filter(user=self.user).exists())


class UsersCourseViewTestCase(AGViewTestBase):
    def setUp(self):
        super().setUp()
        self.client = APIClient()

        self.course = obj_build.make_course()
        self.admin = obj_build.make_admin_user(self.course)
        self.staff = obj_build.make_staff_user(self.course)
        self.student = obj_build.make_student_user(self.course)
        self.handgrader = obj_build.make_handgrader_user(self.course)
        self.guest = obj_build.make_user()

        self.all_users = {
            self.admin,
            self.staff,
            self.student,
            self.handgrader,
            self.guest,
        }

    def test_self_list_courses_is_admin_for(self):
        self.do_list_objects_test(
            self.client, self.admin,
            user_url(self.admin, 'courses-is-admin-for'),
            [self.course.to_dict()])

        for user in self.all_users - {self.admin}:
            self.do_list_objects_test(
                self.client, user, user_url(user, 'courses-is-admin-for'), [])

    def test_other_list_courses_is_admin_for_forbidden(self):
        self.do_permission_denied_get_test(
            self.client, self.guest,
            reverse('courses-is-admin-for', kwargs={'pk': self.admin.pk}))

    def test_self_list_courses_is_staff_for(self):
        self.do_list_objects_test(
            self.client, self.staff,
            user_url(self.staff, 'courses-is-staff-for'), [self.course.to_dict()])

        # Note: Even though admins have staff privileges, they are not
        # listed here with other staff members.
        for user in self.all_users - {self.staff}:
            self.do_list_objects_test(
                self.client, user, user_url(user, 'courses-is-staff-for'), [])

    def test_other_list_courses_is_staff_for_forbidden(self):
        self.do_permission_denied_get_test(
            self.client, self.guest,
            reverse('courses-is-staff-for', kwargs={'pk': self.staff.pk}))

    def test_self_list_courses_is_enrolled_in(self):
        self.do_list_objects_test(
            self.client, self.student,
            user_url(self.student, 'courses-is-enrolled-in'),
            [course.to_dict() for course in self.student.courses_is_enrolled_in.all()])

        for user in self.all_users - {self.student}:
            self.do_list_objects_test(
                self.client, user, user_url(user, 'courses-is-enrolled-in'), [])

    def test_other_list_courses_is_enrolled_in_forbidden(self):
        self.do_permission_denied_get_test(
            self.client, self.guest,
            reverse('courses-is-enrolled-in', kwargs={'pk': self.student.pk}))

    def test_self_list_courses_is_handgrader_for(self):
        self.do_list_objects_test(
            self.client, self.student,
            user_url(self.student, 'courses-is-handgrader-for'),
            [course.to_dict() for course in self.student.courses_is_handgrader_for.all()])

        for user in self.all_users - {self.handgrader}:
            self.do_list_objects_test(
                self.client, user, user_url(user, 'courses-is-handgrader-for'), [])

    def test_other_list_courses_is_handgrader_for_forbidden(self):
        self.do_permission_denied_get_test(
            self.client, self.guest,
            reverse('courses-is-handgrader-for', kwargs={'pk': self.handgrader.pk}))


class UserGroupsTestCase(AGViewTestBase):
    def setUp(self):
        super().setUp()
        self.client = APIClient()

    def test_self_list_groups_is_member_of(self):
        student_group1 = obj_build.make_group()
        student_group2 = ag_models.Group.objects.validate_and_create(
            members=list(student_group1.members.all()),
            project=obj_build.make_project(student_group1.project.course)
        )
        user = student_group1.members.first()
        self.do_list_objects_test(
            self.client,
            user,
            user_url(user, 'groups-is-member-of'),
            [student_group1.to_dict(), student_group2.to_dict()]
        )

        guest_group = obj_build.make_group(members_role=obj_build.UserRole.guest)
        user = guest_group.members.first()
        self.do_list_objects_test(
            self.client, user, user_url(user, 'groups-is-member-of'), [guest_group.to_dict()])

        other_user = obj_build.make_user()
        self.do_list_objects_test(
            self.client, other_user, user_url(other_user, 'groups-is-member-of'), [])

    def test_other_list_groups_is_member_of_forbidden(self):
        group = obj_build.make_group()
        other_user = obj_build.make_user()
        self.do_permission_denied_get_test(
            self.client, other_user, user_url(group.members.first(), 'groups-is-member-of'))

    def test_self_list_invitations_received(self):
        invitation = obj_build.make_group_invitation()
        recipient = invitation.recipients.first()
        self.do_list_objects_test(
            self.client, recipient,
            user_url(recipient, 'group-invitations-received'), [invitation.to_dict()])

        other_user = obj_build.make_user()
        self.do_list_objects_test(
            self.client, other_user, user_url(other_user, 'group-invitations-received'), [])

    def test_other_list_invitations_received_forbidden(self):
        invitation = obj_build.make_group_invitation()
        other_user = obj_build.make_user()
        self.do_permission_denied_get_test(
            self.client, other_user,
            user_url(invitation.sender, 'group-invitations-received'))

    def test_self_list_invitations_sent(self):
        invitation = obj_build.make_group_invitation()
        sender = invitation.sender
        self.do_list_objects_test(
            self.client, sender,
            user_url(sender, 'group-invitations-sent'), [invitation.to_dict()])

        other_user = obj_build.make_user()
        self.do_list_objects_test(
            self.client, other_user, user_url(other_user, 'group-invitations-sent'), [])

    def test_other_list_invitations_sent_forbidden(self):
        invitation = obj_build.make_group_invitation()
        other_user = obj_build.make_user()
        self.do_permission_denied_get_test(
            self.client, other_user,
            user_url(invitation.sender, 'group-invitations-sent'))


def user_url(user, lookup='user-detail'):
    return reverse(lookup, kwargs={'pk': user.pk})


class CurrentUserCanCreateCoursesViewTestCase(UnitTestBase):
    def setUp(self):
        super().setUp()
        self.client = APIClient()
        self.user = obj_build.make_user()
        self.client.force_authenticate(self.user)

    def test_current_user_can_create_courses(self):
        self.user.user_permissions.add(Permission.objects.get(codename='create_course'))
        response = self.client.get(reverse('user-can-create-courses'))
        self.assertTrue(response.data)

    def test_current_user_cannot_create_courses(self):
        response = self.client.get(reverse('user-can-create-courses'))
        self.assertFalse(response.data)
