from datetime import timedelta

from django.contrib.auth.models import Permission, User
from rest_framework.test import APIClient
from django.urls import reverse
from rest_framework import status
from django.utils import timezone

from autograder.utils.testing import UnitTestBase
import autograder.utils.testing.model_obj_builders as obj_build
import autograder.core.models as ag_models


class LateDayTestBase(UnitTestBase):
    def setUp(self):
        super().setUp()
        self.client = APIClient()

        self.initial_num_late_days = 4
        self.course = obj_build.make_course(num_late_days=self.initial_num_late_days)


class ListUserLateDayUsageHistoryViewTestCase(LateDayTestBase):
    def test_student_view_user_late_day_usage_history_permission_denied(self):
        student = obj_build.make_student_user(self.course)

        self.client.force_authenticate(student)
        response = self.client.get(self.get_pk_url(student, self.course))
        self.assertEqual(status.HTTP_403_FORBIDDEN, response.status_code)

        response = self.client.get(self.get_username_url(student, self.course))
        self.assertEqual(status.HTTP_403_FORBIDDEN, response.status_code)

    def test_guest_view_user_late_day_usage_history_permission_denied(self):
        guest = obj_build.make_user()
        student = obj_build.make_student_user(self.course)

        self.client.force_authenticate(guest)
        response = self.client.get(self.get_pk_url(student, self.course))
        self.assertEqual(status.HTTP_403_FORBIDDEN, response.status_code)

    def test_student_view_other_student_late_day_usage_history_permission_denied(self):
        student1 = obj_build.make_student_user(self.course)
        student2 = obj_build.make_student_user(self.course)

        self.client.force_authenticate(student1)
        response = self.client.get(self.get_pk_url(student2, self.course))
        self.assertEqual(status.HTTP_403_FORBIDDEN, response.status_code)

        response = self.client.get(self.get_username_url(student2, self.course))
        self.assertEqual(status.HTTP_403_FORBIDDEN, response.status_code)

    def test_staff_view_user_late_day_usage_history(self):
        staff = obj_build.make_staff_user(self.course)
        student = obj_build.make_student_user(self.course)
        self.do_get_user_late_day_usage_history_test(
            staff, student, self.course, 0, 0)

    def test_admin_view_user_late_day_usage_history(self):
        admin = obj_build.make_admin_user(self.course)
        student = obj_build.make_student_user(self.course)
        self.do_get_user_late_day_usage_history_test(
            admin, student, self.course, 0, 0)

    def test_staff_view_user_late_day_history_for_other_course_permission_denied(self):
        staff = obj_build.make_staff_user(self.course)

        # Student for other course
        other_course = obj_build.make_course()
        other_course_student = obj_build.make_student_user(other_course)
        self.assertFalse(other_course.is_staff(staff))

        self.client.force_authenticate(staff)
        response = self.client.get(self.get_pk_url(other_course_student, other_course))
        self.assertEqual(status.HTTP_403_FORBIDDEN, response.status_code)

        response = self.client.get(self.get_username_url(
            other_course_student, other_course))
        self.assertEqual(status.HTTP_403_FORBIDDEN, response.status_code)

        # Guest for other course
        other_guest = obj_build.make_user()
        response = self.client.get(self.get_pk_url(other_guest, other_course))
        self.assertEqual(status.HTTP_403_FORBIDDEN, response.status_code)

        response = self.client.get(self.get_username_url(other_guest, other_course))
        self.assertEqual(status.HTTP_403_FORBIDDEN, response.status_code)

    def test_get_multiple_late_day_usages(self):
        yesterday = timezone.now() - timedelta(days=1) + timedelta(hours=1)
        day_before_yesterday = yesterday - timedelta(days=1)

        staff = obj_build.make_staff_user(self.course)

        project1 = obj_build.make_project(
            self.course,
            closing_time=day_before_yesterday,
            visible_to_students=True,
            allow_late_days=True
        )
        project2 = obj_build.make_project(
            self.course,
            closing_time=yesterday,
            visible_to_students=True,
            allow_late_days=True
        )
        group1 = obj_build.make_group(project=project1, members_role=obj_build.UserRole.student)
        group2 = obj_build.make_group(project=project2, members_role=obj_build.UserRole.student)
        other_group = obj_build.make_group(
            project=project1, members_role=obj_build.UserRole.student)

        student = group1.members.first()
        other_student = other_group.members.first()

        group2.members.add(student)
        group2.save()

        # student is part of group1 and group2 and submits to each. The first
        # submission uses 2 late days, and the second uses 1
        self.client.force_authenticate(student)
        submit_url_1 = reverse('submissions', kwargs={'pk': group1.pk})
        submit_url_2 = reverse('submissions', kwargs={'pk': group2.pk})

        resp = self.client.post(submit_url_1, {'submitted_files': []}, format='multipart')
        self.assertEqual(status.HTTP_201_CREATED, resp.status_code, msg=resp.data)
        resp = self.client.post(submit_url_2, {'submitted_files': []}, format='multipart')
        self.assertEqual(status.HTTP_201_CREATED, resp.status_code, msg=resp.data)

        # other_student submits for other_group, using 2 late days. This shouldn't
        # show up in get request for student
        self.client.force_authenticate(other_student)
        other_submit_url = reverse('submissions', kwargs={'pk': other_group.pk})
        resp = self.client.post(other_submit_url, {'submitted_files': []}, format='multipart')
        self.assertEqual(status.HTTP_201_CREATED, resp.status_code, msg=resp.data)

        self.do_get_user_late_day_usage_history_test(
            staff, student, self.course,
            expected_num_usage_objects=2,
            expected_num_late_days_used=3
        )

    def do_get_user_late_day_usage_history_test(
        self, requestor: User, requestee: User, course: ag_models.Course,
        expected_num_usage_objects: int, expected_num_late_days_used
    ):
        self.client.force_authenticate(requestor)

        for url in (
            self.get_pk_url(requestee, course), self.get_username_url(requestee, course)
        ):
            response = self.client.get(url)

            self.assertEqual(status.HTTP_200_OK, response.status_code)
            self.assertEqual(expected_num_usage_objects, len(response.data))
            self.assertEqual(expected_num_late_days_used, sum(
                [usage['num_late_days_used'] for usage in response.data]))

    def get_pk_url(self, requestee: User, course: ag_models.Course):
        return reverse(
            'user-late-day-usage-history',
            kwargs={'course_pk': course.pk, 'username_or_pk': requestee.pk}
        )

    def get_username_url(self, requestee: User, course: ag_models.Course):
        return reverse(
            'user-late-day-usage-history',
            kwargs={'course_pk': course.pk, 'username_or_pk': requestee.username}
        )


class ListLateDayUsageHistoryViewTestCase(LateDayTestBase):
    def test_student_view_permission_denied(self):
        student = obj_build.make_student_user(self.course)
        self.client.force_authenticate(student)
        response = self.client.get(self.get_url(self.course))
        self.assertEqual(status.HTTP_403_FORBIDDEN, response.status_code)

    def test_guest_view_permission_denied(self):
        guest = obj_build.make_user()
        self.client.force_authenticate(guest)
        response = self.client.get(self.get_url(self.course))
        self.assertEqual(status.HTTP_403_FORBIDDEN, response.status_code)

    def test_staff_from_other_course_permission_denied(self):
        other_course = obj_build.make_course()
        staff = obj_build.make_staff_user(other_course)
        self.assertFalse(self.course.is_staff(staff))

        self.client.force_authenticate(staff)
        response = self.client.get(self.get_url(self.course))
        self.assertEqual(status.HTTP_403_FORBIDDEN, response.status_code)

    def test_staff_view_empty_list(self):
        staff = obj_build.make_staff_user(self.course)
        self.client.force_authenticate(staff)
        response = self.client.get(self.get_url(self.course))
        self.assertEqual(status.HTTP_200_OK, response.status_code)
        self.assertEqual([], response.data)

    def test_admin_view_all_late_day_usages(self):
        admin = obj_build.make_admin_user(self.course)
        yesterday = timezone.now() - timedelta(days=1) + timedelta(hours=1)
        project = obj_build.make_project(
            self.course,
            closing_time=yesterday,
            visible_to_students=True,
            allow_late_days=True
        )
        group = obj_build.make_group(project=project, members_role=obj_build.UserRole.student)
        student = group.members.first()

        self.client.force_authenticate(student)
        resp = self.client.post(
            reverse('submissions', kwargs={'pk': group.pk}),
            {'submitted_files': []}, format='multipart'
        )
        self.assertEqual(status.HTTP_201_CREATED, resp.status_code, msg=resp.data)

        self.client.force_authenticate(admin)
        response = self.client.get(self.get_url(self.course))
        self.assertEqual(status.HTTP_200_OK, response.status_code)
        self.assertEqual(1, len(response.data))

    def test_staff_view_all_late_day_usages_multiple_students(self):
        day_before_yesterday = timezone.now() - timedelta(days=2) + timedelta(hours=1)

        staff = obj_build.make_staff_user(self.course)

        project = obj_build.make_project(
            self.course,
            closing_time=day_before_yesterday,
            visible_to_students=True,
            allow_late_days=True
        )

        group1 = obj_build.make_group(project=project, members_role=obj_build.UserRole.student)
        group2 = obj_build.make_group(project=project, members_role=obj_build.UserRole.student)

        student1 = group1.members.first()
        student2 = group2.members.first()

        # student1 and student2 each submit to their own group (1 usage record each)
        self.client.force_authenticate(student1)
        resp = self.client.post(
            reverse('submissions', kwargs={'pk': group1.pk}),
            {'submitted_files': []}, format='multipart'
        )
        self.assertEqual(status.HTTP_201_CREATED, resp.status_code, msg=resp.data)

        self.client.force_authenticate(student2)
        resp = self.client.post(
            reverse('submissions', kwargs={'pk': group2.pk}),
            {'submitted_files': []}, format='multipart'
        )
        self.assertEqual(status.HTTP_201_CREATED, resp.status_code, msg=resp.data)

        self.client.force_authenticate(staff)
        response = self.client.get(self.get_url(self.course))
        self.assertEqual(status.HTTP_200_OK, response.status_code)
        self.assertEqual(2, len(response.data))
        user_pks = {usage['user_pk'] for usage in response.data}
        self.assertIn(student1.pk, user_pks)
        self.assertIn(student2.pk, user_pks)

    def test_does_not_include_other_course_usages(self):
        yesterday = timezone.now() - timedelta(days=1) + timedelta(hours=1)
        staff = obj_build.make_staff_user(self.course)

        # Set up a usage in self.course
        project = obj_build.make_project(
            self.course,
            closing_time=yesterday,
            visible_to_students=True,
            allow_late_days=True
        )
        group = obj_build.make_group(project=project, members_role=obj_build.UserRole.student)
        student = group.members.first()
        self.client.force_authenticate(student)
        resp = self.client.post(
            reverse('submissions', kwargs={'pk': group.pk}),
            {'submitted_files': []}, format='multipart'
        )
        self.assertEqual(status.HTTP_201_CREATED, resp.status_code, msg=resp.data)

        # Set up a usage in another course
        other_course = obj_build.make_course(num_late_days=self.initial_num_late_days)
        other_project = obj_build.make_project(
            other_course,
            closing_time=yesterday,
            visible_to_students=True,
            allow_late_days=True
        )
        other_group = obj_build.make_group(
            project=other_project, members_role=obj_build.UserRole.student)
        other_student = other_group.members.first()
        self.client.force_authenticate(other_student)
        resp = self.client.post(
            reverse('submissions', kwargs={'pk': other_group.pk}),
            {'submitted_files': []}, format='multipart'
        )
        self.assertEqual(status.HTTP_201_CREATED, resp.status_code, msg=resp.data)

        self.client.force_authenticate(staff)
        response = self.client.get(self.get_url(self.course))
        self.assertEqual(status.HTTP_200_OK, response.status_code)
        self.assertEqual(1, len(response.data))
        self.assertEqual(self.course.pk, response.data[0]['course'])

    def get_url(self, course: ag_models.Course):
        return reverse('late-day-usage-history', kwargs={'course_pk': course.pk})


class UserLateDaysViewTestCase(LateDayTestBase):
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

        # TODO: remove deprecated URL test when the endpoint is removed
        response = self.client.put(self.get_deprecated_pk_url(student, self.course),
                                   {'late_days_remaining': 42})
        self.assertEqual(status.HTTP_200_OK, response.status_code)
        self.assertEqual({'late_days_remaining': 42}, response.data)

        remaining = ag_models.LateDaysRemaining.objects.get(user=student, course=self.course)
        self.assertEqual(42, remaining.late_days_remaining)
        # end TODO

        response = self.client.put(self.get_pk_url(student, self.course),
                                   {'late_days_remaining': 311})
        self.assertEqual(status.HTTP_200_OK, response.status_code)
        self.assertEqual({'late_days_remaining': 311}, response.data)

        remaining = ag_models.LateDaysRemaining.objects.get(user=student, course=self.course)
        self.assertEqual(311, remaining.late_days_remaining)

    def test_admin_change_late_day_count_by_username(self):
        admin = obj_build.make_admin_user(self.course)
        student = obj_build.make_student_user(self.course)

        self.client.force_authenticate(admin)

        # TODO: remove deprecated URL test when the endpoint is removed
        response = self.client.put(self.get_deprecated_username_url(student, self.course),
                                   {'late_days_remaining': 42})
        self.assertEqual(status.HTTP_200_OK, response.status_code)
        self.assertEqual({'late_days_remaining': 42}, response.data)

        remaining = ag_models.LateDaysRemaining.objects.get(user=student, course=self.course)
        self.assertEqual(42, remaining.late_days_remaining)
        # end TODO

        response = self.client.put(self.get_username_url(student, self.course),
                                   {'late_days_remaining': 311})
        self.assertEqual(status.HTTP_200_OK, response.status_code)
        self.assertEqual({'late_days_remaining': 311}, response.data)

        remaining = ag_models.LateDaysRemaining.objects.get(user=student, course=self.course)
        self.assertEqual(311, remaining.late_days_remaining)

    def test_admin_change_late_day_count_by_pk_object_exists(self):
        admin = obj_build.make_admin_user(self.course)
        student = obj_build.make_student_user(self.course)

        ag_models.LateDaysRemaining.objects.validate_and_create(user=student, course=self.course)
        self.do_get_late_days_test(admin, student, self.course, self.initial_num_late_days)

        self.client.force_authenticate(admin)
        response = self.client.put(self.get_deprecated_pk_url(student, self.course),
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

        # TODO: remove deprecated URL test when the endpoint is removed
        response = self.client.put(self.get_deprecated_username_url(student, self.course),
                                   {'late_days_remaining': 27})
        self.assertEqual(status.HTTP_200_OK, response.status_code)
        self.assertEqual({'late_days_remaining': 27}, response.data)

        remaining = ag_models.LateDaysRemaining.objects.get(user=student, course=self.course)
        self.assertEqual(27, remaining.late_days_remaining)
        # end TODO

        response = self.client.put(self.get_username_url(student, self.course),
                                   {'late_days_remaining': 101})
        self.assertEqual(status.HTTP_200_OK, response.status_code)
        self.assertEqual({'late_days_remaining': 101}, response.data)

        remaining = ag_models.LateDaysRemaining.objects.get(user=student, course=self.course)
        self.assertEqual(101, remaining.late_days_remaining)

    def test_admin_change_late_day_count_for_other_course_permission_denied(self):
        admin = obj_build.make_admin_user(self.course)

        # Student for other course
        other_course = obj_build.make_course()
        other_course_student = obj_build.make_student_user(other_course)
        self.assertFalse(other_course.is_admin(admin))

        self.client.force_authenticate(admin)

        # TODO: remove deprecated URL test when the endpoint is removed
        response = self.client.put(self.get_deprecated_pk_url(other_course_student, other_course),
                                   {'late_days_remaining': 10})
        self.assertEqual(status.HTTP_403_FORBIDDEN, response.status_code)

        # Guest for other course
        other_guest = obj_build.make_user()
        response = self.client.put(self.get_deprecated_pk_url(other_guest, other_course),
                                   {'late_days_remaining': 7})
        self.assertEqual(status.HTTP_403_FORBIDDEN, response.status_code)
        # end TODO

        response = self.client.put(self.get_pk_url(other_course_student, other_course),
                                   {'late_days_remaining': 10})
        self.assertEqual(status.HTTP_403_FORBIDDEN, response.status_code)

        # Guest for other course
        other_guest = obj_build.make_user()
        response = self.client.put(self.get_pk_url(other_guest, other_course),
                                   {'late_days_remaining': 7})
        self.assertEqual(status.HTTP_403_FORBIDDEN, response.status_code)

    def test_staff_view_late_day_count_for_other_course_permission_denied(self):
        staff = obj_build.make_staff_user(self.course)

        # Student for other course
        other_course = obj_build.make_course()
        other_course_student = obj_build.make_student_user(other_course)
        self.assertFalse(other_course.is_staff(staff))

        self.client.force_authenticate(staff)

        # TODO: remove deprecated URL test when the endpoint is removed
        response = self.client.get(self.get_deprecated_pk_url(other_course_student, other_course))
        self.assertEqual(status.HTTP_403_FORBIDDEN, response.status_code)

        response = self.client.get(self.get_deprecated_username_url(
            other_course_student, other_course))
        self.assertEqual(status.HTTP_403_FORBIDDEN, response.status_code)

        # Guest for other course
        other_guest = obj_build.make_user()
        response = self.client.get(self.get_deprecated_pk_url(other_guest, other_course))
        self.assertEqual(status.HTTP_403_FORBIDDEN, response.status_code)

        response = self.client.get(self.get_deprecated_username_url(other_guest, other_course))
        self.assertEqual(status.HTTP_403_FORBIDDEN, response.status_code)
        # end TODO

        response = self.client.get(self.get_pk_url(other_course_student, other_course))
        self.assertEqual(status.HTTP_403_FORBIDDEN, response.status_code)

        response = self.client.get(self.get_username_url(
            other_course_student, other_course))
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

        # TODO: remove deprecated URL test when the endpoint is removed
        response = self.client.get(self.get_deprecated_pk_url(student2, self.course))
        self.assertEqual(status.HTTP_403_FORBIDDEN, response.status_code)

        response = self.client.get(self.get_deprecated_username_url(student2, self.course))
        self.assertEqual(status.HTTP_403_FORBIDDEN, response.status_code)
        # end TODO

        response = self.client.get(self.get_pk_url(student2, self.course))
        self.assertEqual(status.HTTP_403_FORBIDDEN, response.status_code)

        response = self.client.get(self.get_username_url(student2, self.course))
        self.assertEqual(status.HTTP_403_FORBIDDEN, response.status_code)

    def test_guest_view_other_late_day_count_permission_denied(self):
        guest1 = obj_build.make_user()
        guest2 = obj_build.make_user()

        self.client.force_authenticate(guest1)

        # TODO: remove deprecated URL test when the endpoint is removed
        response = self.client.get(self.get_deprecated_pk_url(guest2, self.course))
        self.assertEqual(status.HTTP_403_FORBIDDEN, response.status_code)

        response = self.client.get(self.get_deprecated_username_url(guest2, self.course))
        self.assertEqual(status.HTTP_403_FORBIDDEN, response.status_code)
        # end TODO

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
        """TODO: remove when deprecated endpoint is removed"""
        student = obj_build.make_student_user(self.course)
        self.client.force_authenticate(student)
        url = reverse('deprecated-user-late-days', kwargs={'username_or_pk': student.pk})

        response = self.client.get(url)
        self.assertEqual(status.HTTP_400_BAD_REQUEST, response.status_code)

        response = self.client.put(url, {})
        self.assertEqual(status.HTTP_400_BAD_REQUEST, response.status_code)

    def test_put_missing_body_param(self):
        admin = obj_build.make_admin_user(self.course)
        self.client.force_authenticate(admin)

        # TODO: remove deprecated URL test when the endpoint is removed
        response = self.client.put(self.get_deprecated_pk_url(admin, self.course), {})
        self.assertEqual(status.HTTP_400_BAD_REQUEST, response.status_code)

        response = self.client.put(self.get_deprecated_username_url(admin, self.course), {})
        self.assertEqual(status.HTTP_400_BAD_REQUEST, response.status_code)
        # end TODO

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

        # TODO: remove deprecated URLs when those endpoints are removed
        for url in (
            self.get_deprecated_pk_url(
                requestee, course), self.get_deprecated_username_url(requestee, course),
            self.get_pk_url(requestee, course), self.get_username_url(requestee, course)
        ):
            response = self.client.get(url)

            self.assertEqual(status.HTTP_200_OK, response.status_code)
            self.assertEqual({'late_days_remaining': expected_num_late_days}, response.data)

    def get_deprecated_pk_url(self, requestee: User, course: ag_models.Course):
        """TODO: delete this when deprecated endpoints are removed"""
        url = reverse('deprecated-user-late-days', kwargs={'username_or_pk': requestee.pk})
        return url + f'?course_pk={course.pk}'

    def get_deprecated_username_url(self, requestee: User, course: ag_models.Course):
        """TODO: delete this when deprecated endpoints are removed"""
        url = reverse('deprecated-user-late-days', kwargs={'username_or_pk': requestee.username})
        return url + f'?course_pk={course.pk}'

    def get_pk_url(self, requestee: User, course: ag_models.Course):
        return reverse('user-late-days', kwargs={
            'course_pk': course.pk, 'username_or_pk': requestee.pk}
        )

    def get_username_url(self, requestee: User, course: ag_models.Course):
        return reverse('user-late-days', kwargs={
            'course_pk': course.pk, 'username_or_pk': requestee.username}
        )
