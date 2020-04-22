import itertools

from django.contrib.auth.models import User, Permission
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APIClient

import autograder.core.models as ag_models
import autograder.utils.testing.model_obj_builders as obj_build
from autograder.utils.testing import UnitTestBase
from autograder.rest_api.tests.test_views.ag_view_test_base import AGViewTestBase
from autograder.rest_api.serialize_user import serialize_user


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
        recipient = invitation.invited_users.first()
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
            user_url(invitation.invitation_creator, 'group-invitations-received'))

    def test_self_list_invitations_sent(self):
        invitation = obj_build.make_group_invitation()
        sender = invitation.invitation_creator
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
            user_url(invitation.invitation_creator, 'group-invitations-sent'))


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


class UserLateDaysViewTestCase(UnitTestBase):
    def setUp(self):
        super().setUp()
        self.client = APIClient()

        self.initial_num_late_days = 4
        self.course = obj_build.make_course(num_late_days=self.initial_num_late_days)

    def test_student_view_own_late_day_count(self):
        student = obj_build.make_student_user(self.course)
        self.do_get_late_days_test(student, student, self.course, self.initial_num_late_days)

    def test_guest_view_own_late_day_count(self):
        guest = obj_build.make_user()
        self.do_get_late_days_test(guest, guest, self.course, self.initial_num_late_days)

    def test_staff_view_other_late_day_count(self):
        staff = obj_build.make_staff_user(self.course)
        student = obj_build.make_student_user(self.course)
        self.do_get_late_days_test(staff, student, self.course, self.initial_num_late_days)

    def test_admin_change_late_day_count_by_pk(self):
        admin = obj_build.make_admin_user(self.course)
        student = obj_build.make_student_user(self.course)

        self.client.force_authenticate(admin)
        response = self.client.put(self.get_pk_url(student, self.course),
                                   {'late_days_remaining': 42})
        self.assertEqual(status.HTTP_200_OK, response.status_code)
        self.assertEqual({'late_days_remaining': 42}, response.data)

        remaining = ag_models.LateDaysRemaining.objects.get(user=student, course=self.course)
        self.assertEqual(42, remaining.late_days_remaining)

    def test_admin_change_late_day_count_by_username(self):
        admin = obj_build.make_admin_user(self.course)
        student = obj_build.make_student_user(self.course)

        self.client.force_authenticate(admin)
        response = self.client.put(self.get_username_url(student, self.course),
                                   {'late_days_remaining': 42})
        self.assertEqual(status.HTTP_200_OK, response.status_code)
        self.assertEqual({'late_days_remaining': 42}, response.data)

        remaining = ag_models.LateDaysRemaining.objects.get(user=student, course=self.course)
        self.assertEqual(42, remaining.late_days_remaining)

    def test_admin_change_late_day_count_by_pk_object_exists(self):
        admin = obj_build.make_admin_user(self.course)
        student = obj_build.make_student_user(self.course)

        ag_models.LateDaysRemaining.objects.validate_and_create(user=student, course=self.course)
        self.do_get_late_days_test(admin, student, self.course, self.initial_num_late_days)

        self.client.force_authenticate(admin)
        response = self.client.put(self.get_pk_url(student, self.course),
                                   {'late_days_remaining': 27})
        self.assertEqual(status.HTTP_200_OK, response.status_code)
        self.assertEqual({'late_days_remaining': 27}, response.data)

        remaining = ag_models.LateDaysRemaining.objects.get(user=student, course=self.course)
        self.assertEqual(27, remaining.late_days_remaining)

    def test_admin_change_late_day_count_by_username_object_exists(self):
        admin = obj_build.make_admin_user(self.course)
        student = obj_build.make_student_user(self.course)

        ag_models.LateDaysRemaining.objects.validate_and_create(user=student, course=self.course)
        self.do_get_late_days_test(admin, student, self.course, self.initial_num_late_days)

        self.client.force_authenticate(admin)
        response = self.client.put(self.get_username_url(student, self.course),
                                   {'late_days_remaining': 27})
        self.assertEqual(status.HTTP_200_OK, response.status_code)
        self.assertEqual({'late_days_remaining': 27}, response.data)

        remaining = ag_models.LateDaysRemaining.objects.get(user=student, course=self.course)
        self.assertEqual(27, remaining.late_days_remaining)

    def test_admin_change_late_day_count_for_other_course_permission_denied(self):
        admin = obj_build.make_admin_user(self.course)

        # Student for other course
        other_course = obj_build.make_course()
        other_course_student = obj_build.make_student_user(other_course)
        self.assertFalse(other_course.is_admin(admin))

        self.client.force_authenticate(admin)
        response = self.client.put(self.get_pk_url(other_course_student, other_course),
                                   {'late_days_remaining': 10})
        self.assertEqual(status.HTTP_403_FORBIDDEN, response.status_code)

        response = self.client.put(self.get_username_url(other_course_student, other_course),
                                   {'late_days_remaining': 10})
        self.assertEqual(status.HTTP_403_FORBIDDEN, response.status_code)

        # Guest for other course
        other_guest = obj_build.make_user()
        response = self.client.put(self.get_pk_url(other_guest, other_course),
                                   {'late_days_remaining': 7})
        self.assertEqual(status.HTTP_403_FORBIDDEN, response.status_code)

        other_guest = obj_build.make_user()
        response = self.client.put(self.get_username_url(other_guest, other_course),
                                   {'late_days_remaining': 7})
        self.assertEqual(status.HTTP_403_FORBIDDEN, response.status_code)

    def test_staff_view_late_day_count_for_other_course_permission_denied(self):
        staff = obj_build.make_staff_user(self.course)

        # Student for other course
        other_course = obj_build.make_course()
        other_course_student = obj_build.make_student_user(other_course)
        self.assertFalse(other_course.is_staff(staff))

        self.client.force_authenticate(staff)
        response = self.client.get(self.get_pk_url(other_course_student, other_course))
        self.assertEqual(status.HTTP_403_FORBIDDEN, response.status_code)

        response = self.client.get(self.get_username_url(other_course_student, other_course))
        self.assertEqual(status.HTTP_403_FORBIDDEN, response.status_code)

        # Guest for other course
        other_guest = obj_build.make_user()
        response = self.client.get(self.get_pk_url(other_guest, other_course))
        self.assertEqual(status.HTTP_403_FORBIDDEN, response.status_code)

        response = self.client.get(self.get_username_url(other_guest, other_course))
        self.assertEqual(status.HTTP_403_FORBIDDEN, response.status_code)

    def test_student_view_other_late_day_count_permission_denied(self):
        student1 = obj_build.make_student_user(self.course)
        student2 = obj_build.make_student_user(self.course)

        self.client.force_authenticate(student1)
        response = self.client.get(self.get_pk_url(student2, self.course))
        self.assertEqual(status.HTTP_403_FORBIDDEN, response.status_code)

        response = self.client.get(self.get_username_url(student2, self.course))
        self.assertEqual(status.HTTP_403_FORBIDDEN, response.status_code)

    def test_guest_view_other_late_day_count_permission_denied(self):
        guest1 = obj_build.make_user()
        guest2 = obj_build.make_user()

        self.client.force_authenticate(guest1)
        response = self.client.get(self.get_pk_url(guest2, self.course))
        self.assertEqual(status.HTTP_403_FORBIDDEN, response.status_code)

        response = self.client.get(self.get_username_url(guest2, self.course))
        self.assertEqual(status.HTTP_403_FORBIDDEN, response.status_code)

    def test_get_late_day_count_object_exists(self):
        student = obj_build.make_student_user(self.course)

        remaining: ag_models.LateDaysRemaining = (
            ag_models.LateDaysRemaining.objects.validate_and_create(
                user=student, course=self.course))
        remaining.late_days_remaining -= 1
        remaining.save()

        self.do_get_late_days_test(student, student, self.course, remaining.late_days_remaining)

    def test_missing_course_pk_query_param(self):
        student = obj_build.make_student_user(self.course)
        self.client.force_authenticate(student)
        url = reverse('user-late-days', kwargs={'username_or_pk': student.pk})

        response = self.client.get(url)
        self.assertEqual(status.HTTP_400_BAD_REQUEST, response.status_code)

        response = self.client.put(url, {})
        self.assertEqual(status.HTTP_400_BAD_REQUEST, response.status_code)

    def test_put_missing_body_param(self):
        admin = obj_build.make_admin_user(self.course)
        self.client.force_authenticate(admin)

        response = self.client.put(self.get_pk_url(admin, self.course), {})
        self.assertEqual(status.HTTP_400_BAD_REQUEST, response.status_code)

        response = self.client.put(self.get_username_url(admin, self.course), {})
        self.assertEqual(status.HTTP_400_BAD_REQUEST, response.status_code)

    def test_get_late_days_course_has_no_late_days(self):
        self.course.validate_and_update(num_late_days=0)
        student = obj_build.make_student_user(self.course)
        self.do_get_late_days_test(student, student, self.course, 0)

    def do_get_late_days_test(self, requestor: User, requestee: User, course: ag_models.Course,
                              expected_num_late_days: int):
        self.client.force_authenticate(requestor)

        for url in self.get_pk_url(requestee, course), self.get_username_url(requestee, course):
            response = self.client.get(url)

            self.assertEqual(status.HTTP_200_OK, response.status_code)
            self.assertEqual({'late_days_remaining': expected_num_late_days}, response.data)

    def get_pk_url(self, requestee: User, course: ag_models.Course):
        url = reverse('user-late-days', kwargs={'username_or_pk': requestee.pk})
        return url + f'?course_pk={course.pk}'

    def get_username_url(self, requestee: User, course: ag_models.Course):
        url = reverse('user-late-days', kwargs={'username_or_pk': requestee.username})
        return url + f'?course_pk={course.pk}'
