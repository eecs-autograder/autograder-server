import itertools

from django.contrib.auth.models import User
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APIClient

import autograder.core.models as ag_models
import autograder.rest_api.serializers as ag_serializers
import autograder.rest_api.tests.test_views.common_generic_data as test_data
import autograder.rest_api.tests.test_views.ag_view_test_base as test_impls
import autograder.utils.testing.model_obj_builders as obj_build
from autograder.utils.testing import UnitTestBase


class RetrieveUserTestCase(test_data.Project,
                           test_data.Group,
                           test_impls.GetObjectTest,
                           UnitTestBase):
    def setUp(self):
        super().setUp()
        self.client = APIClient()

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
