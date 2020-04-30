import datetime
from typing import List
from unittest import mock

from django.contrib.auth.models import User
from django.core.files.uploadedfile import SimpleUploadedFile
from django.urls import reverse
from django.utils import timezone
from rest_framework import status
from rest_framework.test import APIClient

import autograder.core.models as ag_models
import autograder.utils.testing.model_obj_builders as obj_build
from autograder.rest_api.serialize_user import serialize_user
from autograder.rest_api.tests.test_views.ag_view_test_base import AGViewTestBase
from autograder.utils.testing import UnitTestBase


class SortedListGroupsTestCase(AGViewTestBase):
    def setUp(self):
        super().setUp()
        self.client = APIClient()

    def test_groups_sorted_by_least_alphabetical_username(self):
        self.maxDiff = None

        project = obj_build.make_project(max_group_size=3, guests_can_submit=True)
        [admin] = obj_build.make_admin_users(project.course, 1)

        group1_user1 = User.objects.create(username='fred')
        group1 = ag_models.Group.objects.validate_and_create(
            members=[group1_user1], project=project)

        group2_user1 = User.objects.create(username='steve')
        group2_user2 = User.objects.create(username='anna')
        group2 = ag_models.Group.objects.validate_and_create(
            members=[group2_user1, group2_user2], project=project)

        group3_user1 = User.objects.create(username='georgina')
        group3_user2 = User.objects.create(username='joe')
        group3_user3 = User.objects.create(username='belinda')
        group3 = ag_models.Group.objects.validate_and_create(
            members=[group3_user1, group3_user2, group3_user3], project=project)

        expected = [group2.to_dict(), group3.to_dict(), group1.to_dict()]  # type: List[dict]
        for group_dict in expected:
            group_dict['member_names'] = list(sorted(group_dict['member_names']))

        self.client.force_authenticate(admin)
        response = self.client.get(reverse('groups', kwargs={'project_pk': project.pk}))
        self.assertEqual(expected, response.data)


class ListGroupsTestCase(AGViewTestBase):
    def setUp(self):
        super().setUp()
        self.client = APIClient()
        self.project = obj_build.make_project()
        self.course = self.project.course
        self.url = reverse('groups', kwargs={'project_pk': self.project.pk})

    def test_admin_list_groups(self):
        admin = obj_build.make_admin_user(self.project.course)
        self.do_list_objects_test(
            self.client, admin, self.url, self.build_groups(self.project), check_order=True)

    def test_staff_list_groups(self):
        staff = obj_build.make_staff_user(self.project.course)
        self.do_list_objects_test(
            self.client, staff, self.url, self.build_groups(self.project), check_order=True)

    def test_student_list_groups_permission_denied(self):
        self.project.validate_and_update(visible_to_students=True)
        student = obj_build.make_student_user(self.project.course)
        self.build_groups(self.project)
        self.do_permission_denied_get_test(self.client, student, self.url)

    def test_handgrader_list_groups(self):
        handgrader = obj_build.make_handgrader_user(self.course)
        self.do_list_objects_test(
            self.client, handgrader, self.url, self.build_groups(self.project))

    def test_guest_list_groups_permission_denied(self):
        self.project.validate_and_update(visible_to_students=True, guests_can_submit=True)
        guest = obj_build.make_user()

        self.build_groups(self.project)
        self.do_permission_denied_get_test(self.client, guest, self.url)

    def test_prefetching_doesnt_skew_num_submissions_and_num_submissions_towards_limit(self):
        self.maxDiff = None

        self.project.validate_and_update(visible_to_students=True, guests_can_submit=True)
        group1 = obj_build.make_group(project=self.project)
        group1_yesterday_submission = obj_build.make_submission(
            group=group1,
            timestamp=timezone.now() - datetime.timedelta(days=1))
        group1_not_towards_limit_submission = obj_build.make_submission(
            group=group1,
            status=ag_models.Submission.GradingStatus.error)
        group1_towards_limit_submission = obj_build.make_submission(group=group1)

        group1.refresh_from_db()
        self.assertEqual(3, group1.num_submissions)
        self.assertEqual(1, group1.num_submits_towards_limit)

        group2 = obj_build.make_group(project=self.project)
        group2_yesterday_submission = obj_build.make_submission(
            group=group2,
            timestamp=timezone.now() - datetime.timedelta(days=1))
        group2_yesterday_submission2 = obj_build.make_submission(
            group=group2,
            timestamp=timezone.now() - datetime.timedelta(days=1))
        group2_not_towards_limit_submission = obj_build.make_submission(
            group=group2,
            status=ag_models.Submission.GradingStatus.removed_from_queue)
        group2_towards_limit_submission = obj_build.make_submission(group=group2)

        group2.refresh_from_db()
        self.assertEqual(4, group2.num_submissions)
        self.assertEqual(1, group2.num_submits_towards_limit)

        admin = obj_build.make_admin_user(self.course)
        self.client.force_authenticate(admin)
        response = self.client.get(self.url)
        self.assertEqual(status.HTTP_200_OK, response.status_code)

        self.assertCountEqual([group1.to_dict(), group2.to_dict()], response.data)

    def build_groups(self, project):
        project.validate_and_update(guests_can_submit=True)
        obj_build.make_group(members_role=obj_build.UserRole.admin, project=self.project)
        obj_build.make_group(members_role=obj_build.UserRole.staff, project=self.project)
        obj_build.make_group(members_role=obj_build.UserRole.student, project=self.project)
        obj_build.make_group(members_role=obj_build.UserRole.guest, project=self.project)

        serialized_groups = [group.to_dict() for group in project.groups.all()]
        self.assertEqual(4, len(serialized_groups))
        return serialized_groups


class CreateGroupTestCase(AGViewTestBase):
    def setUp(self):
        super().setUp()
        self.client = APIClient()
        self.project = obj_build.make_project()
        self.admin = obj_build.make_admin_user(self.project.course)
        self.url = reverse('groups', kwargs={'project_pk': self.project.pk})

    def test_admin_create_enrolled_group(self):
        args = {'member_names': self.get_legal_member_names()}
        self.do_create_object_test(self.project.groups,
                                   self.client, self.admin, self.url, args)

    def test_admin_create_non_enrolled_group(self):
        self.project.validate_and_update(guests_can_submit=True)
        args = {'member_names': ['not_enrolled1', 'not_enrolled2']}
        self.do_create_object_test(self.project.groups, self.client, self.admin, self.url, args)

    def test_admin_create_group_override_size(self):
        self.project.validate_and_update(max_group_size=1)
        args = {'member_names': self.get_legal_member_names()}

        self.do_create_object_test(self.project.groups, self.client, self.admin, self.url, args)

    def test_admin_create_group_error_invalid_members(self):
        student = obj_build.make_student_user(self.project.course)
        guest = obj_build.make_user()
        args = {'member_names': [student.username, guest.username]}
        self.do_invalid_create_object_test(
            self.project.groups, self.client, self.admin, self.url, args)

    def test_admin_create_group_error_non_allowed_domain_guest(self):
        self.project.course.validate_and_update(allowed_guest_domain='@llama.edu')
        self.project.validate_and_update(guests_can_submit=True)
        allowed_guest = obj_build.make_allowed_domain_guest_user(self.project.course)
        non_allowed_guest = obj_build.make_user()

        args = {'member_names': [allowed_guest.username, non_allowed_guest.username]}
        self.do_invalid_create_object_test(
            self.project.groups, self.client, self.admin, self.url, args)

    def test_admin_create_group_missing_member_names(self):
        self.do_invalid_create_object_test(
            self.project.groups, self.client, self.admin, self.url, {})

    def test_non_admin_create_group_permission_denied(self):
        self.project.validate_and_update(visible_to_students=True, guests_can_submit=True)

        staff = obj_build.make_staff_user(self.project.course)
        student = obj_build.make_student_user(self.project.course)
        handgrader = obj_build.make_handgrader_user(self.project.course)
        guest = obj_build.make_user()

        args = {'member_names': self.get_legal_member_names()}
        for user in staff, student, handgrader, guest:
            self.do_permission_denied_create_test(
                self.project.groups, self.client, user, self.url, args)

    def get_legal_members(self):
        if hasattr(self, '_legal_members'):
            return self._legal_members

        self.project.validate_and_update(max_group_size=3)
        self._legal_members = obj_build.create_dummy_users(2)
        self.project.course.students.add(*self._legal_members)
        return self._legal_members

    def get_legal_member_names(self):
        members = self.get_legal_members()
        return [member.username for member in members]


class CreateSoloGroupTestCase(AGViewTestBase):
    def setUp(self):
        super().setUp()
        self.client = APIClient()
        self.project = obj_build.make_project()
        self.course = self.project.course
        self.url = reverse('solo_group', kwargs={'project_pk': self.project.pk})

    def test_staff_create_solo_group_min_size_one(self) -> None:
        staff = obj_build.make_staff_user(self.course)
        admin = obj_build.make_admin_user(self.course)
        for user in admin, staff:
            response = self.do_create_object_test(
                self.project.groups, self.client, user, self.url, {}, check_data=False)
            self.assertCountEqual([user.username], response.data['member_names'])

    def test_student_create_solo_group_min_size_one(self):
        self.project.validate_and_update(visible_to_students=True)
        student = obj_build.make_student_user(self.course)

        response = self.do_create_object_test(
            self.project.groups, self.client, student, self.url, {}, check_data=False)
        self.assertCountEqual([student.username], response.data['member_names'])

    def test_guest_create_solo_group_min_size_one(self):
        self.project.validate_and_update(visible_to_students=True, guests_can_submit=True)
        guest = obj_build.make_user()

        response = self.do_create_object_test(
            self.project.groups, self.client, guest, self.url, {}, check_data=False)
        self.assertCountEqual([guest.username], response.data['member_names'])

    def test_staff_create_solo_group_min_size_not_one(self) -> None:
        staff = obj_build.make_staff_user(self.course)
        self.project.validate_and_update(min_group_size=2, max_group_size=2)
        response = self.do_create_object_test(
            self.project.groups, self.client, staff, self.url, {}, check_data=False)
        self.assertCountEqual([staff.username], response.data['member_names'])

    def test_student_or_guest_create_solo_group_min_size_not_one_invalid(self):
        self.project.validate_and_update(
            visible_to_students=True,
            guests_can_submit=True,
            min_group_size=2,
            max_group_size=2
        )
        student = obj_build.make_student_user(self.course)
        guest = obj_build.make_user()

        for user in student, guest:
            self.do_invalid_create_object_test(
                self.project.groups, self.client, user, self.url, {})

    def test_handgrader_create_solo_group_permission_denied(self):
        self.project.validate_and_update(visible_to_students=True)
        handgrader = obj_build.make_handgrader_user(self.course)
        self.do_permission_denied_create_test(
            self.project.groups, self.client, handgrader, self.url, {})

    def test_handgrader_create_solo_group_when_also_student(self):
        self.project.validate_and_update(visible_to_students=True)
        handgrader = obj_build.make_handgrader_user(self.course)
        self.project.course.students.add(handgrader)
        self.do_create_object_test(self.project.groups, self.client, handgrader, self.url, {})

    def test_student_create_solo_group_project_hidden_permission_denied(self):
        self.project.validate_and_update(guests_can_submit=True)
        student = obj_build.make_student_user(self.course)
        guest = obj_build.make_user()

        for user in student, guest:
            self.do_permission_denied_create_test(
                self.project.groups, self.client, user, self.url, {})

    def test_guest_create_solo_group_wrong_username_domain_invalid(self) -> None:
        self.project.validate_and_update(visible_to_students=True, guests_can_submit=True)
        self.course.validate_and_update(allowed_guest_domain='@waa.net')

        right_domain_guest = obj_build.make_allowed_domain_guest_user(self.course)
        response = self.do_create_object_test(
            self.project.groups, self.client, right_domain_guest, self.url, {}, check_data=False)
        self.assertCountEqual([right_domain_guest.username], response.data['member_names'])

        wrong_domain_guest = obj_build.make_user()
        self.do_invalid_create_object_test(
            self.project.groups, self.client, wrong_domain_guest, self.url, {})

    def test_non_enrolled_create_solo_group_project_private_permission_denied(self):
        self.project.validate_and_update(visible_to_students=True)
        self.do_permission_denied_create_test(
            self.project.groups, self.client, obj_build.make_user(), self.url, {})


class RetrieveGroupTestCase(AGViewTestBase):
    def setUp(self):
        super().setUp()
        self.client = APIClient()
        self.project = obj_build.make_project()
        self.course = self.project.course

    def test_admin_or_staff_get_group(self):
        admin = obj_build.make_admin_user(self.course)
        staff = obj_build.make_staff_user(self.course)

        for user in admin, staff:
            student_group = obj_build.make_group(project=self.project)
            self.do_get_object_test(
                self.client, user, self.group_url(student_group), student_group.to_dict())

            guest_group = obj_build.make_group(
                project=self.project, members_role=obj_build.UserRole.guest)
            self.do_get_object_test(
                self.client, user, self.group_url(guest_group), guest_group.to_dict())

            admin_group = obj_build.make_group(
                project=self.project, members_role=obj_build.UserRole.admin)
            self.do_get_object_test(
                self.client, user, self.group_url(admin_group), admin_group.to_dict())

    def test_student_get_group(self):
        self.project.validate_and_update(visible_to_students=True)
        group = obj_build.make_group(project=self.project)
        self.do_get_object_test(
            self.client, group.members.first(), self.group_url(group), group.to_dict())

    def test_guest_get_group(self):
        self.project.validate_and_update(visible_to_students=True, guests_can_submit=True)
        group = obj_build.make_group(project=self.project, members_role=obj_build.UserRole.guest)
        self.do_get_object_test(
            self.client, group.members.first(), self.group_url(group), group.to_dict())

    def test_non_member_get_group_permission_denied(self):
        self.project.validate_and_update(visible_to_students=True)
        group = obj_build.make_group(project=self.project)

        non_member = obj_build.make_student_user(self.course)
        self.do_permission_denied_get_test(self.client, non_member, self.group_url(group))

    def test_student_get_group_project_hidden_permission_denied(self):
        group = obj_build.make_group(project=self.project)
        self.do_permission_denied_get_test(
            self.client, group.members.first(), self.group_url(group))

    def test_guest_get_group_project_hidden_permission_denied(self):
        self.project.validate_and_update(guests_can_submit=True)
        group = obj_build.make_group(project=self.project, members_role=obj_build.UserRole.guest)
        self.do_permission_denied_get_test(
            self.client, group.members.first(), self.group_url(group))

    def test_guest_get_group_project_private_permission_denied(self):
        self.project.validate_and_update(visible_to_students=True, guests_can_submit=True)
        group = ag_models.Group.objects.validate_and_create(
            project=self.project, members=[obj_build.make_user()])
        self.project.validate_and_update(guests_can_submit=False)

        self.do_permission_denied_get_test(
            self.client, group.members.first(), self.group_url(group))

    def test_handgrader_get_group_permission_denied(self):
        handgrader = obj_build.make_handgrader_user(self.course)

        student_group = obj_build.make_group(project=self.project)
        self.do_permission_denied_get_test(self.client, handgrader, self.group_url(student_group))

        guest_group = obj_build.make_group(
            project=self.project, members_role=obj_build.UserRole.guest)
        self.do_permission_denied_get_test(self.client, handgrader, self.group_url(guest_group))

    def test_prefetching_doesnt_skew_num_submissions_and_num_submissions_towards_limit(self):
        group = obj_build.make_group(project=self.project)
        yesterday_submission = obj_build.make_submission(
            group=group,
            timestamp=timezone.now() - datetime.timedelta(days=1))
        not_towards_limit_submission = obj_build.make_submission(
            group=group,
            status=ag_models.Submission.GradingStatus.removed_from_queue)
        towards_limit_submission = obj_build.make_submission(group=group)

        group.refresh_from_db()
        self.assertEqual(3, group.num_submissions)
        self.assertEqual(1, group.num_submits_towards_limit)

        self.client.force_authenticate(obj_build.make_admin_user(self.course))
        response = self.client.get(self.group_url(group))
        self.assertEqual(status.HTTP_200_OK, response.status_code)
        self.assertEqual(3, response.data['num_submissions'])
        self.assertEqual(1, response.data['num_submits_towards_limit'])

    def group_url(self, group: ag_models.Group) -> str:
        return reverse('group-detail', kwargs={'pk': group.pk})


class UpdateGroupTestCase(AGViewTestBase):
    def setUp(self):
        super().setUp()
        self.new_due_date = timezone.now().replace(microsecond=0)

        self.client = APIClient()
        self.project = obj_build.make_project()
        self.course = self.project.course
        self.admin = obj_build.make_admin_user(self.course)

    def get_names(self, users):
        return list(sorted((user.username for user in users)))

    def test_admin_update_admin_and_staff_group_members(self):
        group = obj_build.make_group(
            num_members=2, members_role=obj_build.UserRole.staff, project=self.project)
        new_members = list(group.members.all())[:-1] + [obj_build.make_admin_user(self.course)]
        response = self.do_patch_object_test(
            group, self.client, self.admin, self.group_url(group),
            {'member_names': self.get_names(new_members)},
            ignore_fields=['members'])

        self.assertGreater(len(new_members), self.project.max_group_size)
        self.assertCountEqual(
            [serialize_user(user) for user in new_members], response.data['members'])

    def test_admin_update_student_group_members(self):
        group = obj_build.make_group(
            num_members=2, members_role=obj_build.UserRole.student, project=self.project)
        new_members = list(group.members.all())[:-1] + [obj_build.make_student_user(self.course)]
        response = self.do_patch_object_test(
            group, self.client, self.admin, self.group_url(group),
            {'member_names': self.get_names(new_members)},
            ignore_fields=['members'])

        self.assertGreater(len(new_members), self.project.max_group_size)
        self.assertCountEqual(
            [serialize_user(user) for user in new_members], response.data['members'])

    def test_admin_update_guest_group_members(self):
        group = obj_build.make_group(
            num_members=2, members_role=obj_build.UserRole.guest, project=self.project)
        new_members = list(group.members.all())[:-1] + [obj_build.make_user()]
        response = self.do_patch_object_test(
            group, self.client, self.admin, self.group_url(group),
            {'member_names': self.get_names(new_members)},
            ignore_fields=['members'])

        self.assertGreater(len(new_members), self.project.max_group_size)
        self.assertCountEqual(
            [serialize_user(user) for user in new_members], response.data['members'])

    def test_admin_update_group_extension(self):
        group = obj_build.make_group(project=self.project)
        self.do_patch_object_test(
            group, self.client, self.admin, self.group_url(group),
            {'extended_due_date': self.new_due_date})
        self.do_patch_object_test(
            group, self.client, self.admin, self.group_url(group),
            {'extended_due_date': None})

    def test_admin_update_group_invalid_members(self):
        group = obj_build.make_group(project=self.project)
        new_members = self.get_names(list(group.members.all())[:-1]) + ['stove']
        response = self.do_patch_object_invalid_args_test(
            group, self.client, self.admin, self.group_url(group),
            {'member_names': new_members})
        self.assertIn('members', response.data)

    def test_admin_update_group_error_non_allowed_domain_guest(self):
        self.course.validate_and_update(allowed_guest_domain='@llama.edu')
        self.project.validate_and_update(guests_can_submit=True)
        allowed_guest = obj_build.make_allowed_domain_guest_user(self.course)

        group = ag_models.Group.objects.validate_and_create(
            members=[allowed_guest], project=self.project
        )

        non_allowed_guest = obj_build.make_user()

        response = self.do_patch_object_invalid_args_test(
            group, self.client, self.admin, self.group_url(group),
            {'member_names': [allowed_guest.username, non_allowed_guest.username]})
        self.assertIn('members', response.data)

    def test_admin_update_group_bad_date(self):
        group = obj_build.make_group(project=self.project)
        response = self.do_patch_object_invalid_args_test(
            group, self.client, self.admin, self.group_url(group),
            {'extended_due_date': 'not a date'})
        self.assertIn('extended_due_date', response.data)

    def test_non_admin_update_group_permission_denied(self):
        group = obj_build.make_group(project=self.project)
        staff = obj_build.make_staff_user(self.course)
        handgrader = obj_build.make_handgrader_user(self.course)
        student = obj_build.make_student_user(self.course)
        guest = obj_build.make_user()
        for user in staff, student, guest, handgrader:
            self.do_patch_object_permission_denied_test(
                group, self.client, user, self.group_url(group),
                {'extended_due_date': self.new_due_date})

    def group_url(self, group: ag_models.Group) -> str:
        return reverse('group-detail', kwargs={'pk': group.pk})


class MergeGroupsTestCase(AGViewTestBase):
    def setUp(self):
        super().setUp()
        self.client = APIClient()

        self.project = obj_build.make_project()
        self.course = self.project.course
        self.admin = obj_build.make_admin_user(self.course)

        self.group1 = obj_build.make_group(project=self.project)
        self.group2 = obj_build.make_group(project=self.project)
        self.original_num_groups = 2
        self.assertEqual(self.original_num_groups, ag_models.Group.objects.count())

    def test_normal_merge(self):
        files = []
        for i in range(2):
            file_name = 'whatever_you_want' + str(i)
            ag_models.ExpectedStudentFile.objects.create(
                pattern=file_name, project=self.project)
            files.append(
                SimpleUploadedFile(file_name,
                                   ('heeey' + str(i)).encode('utf-8')))

        for i in range(2):
            obj_build.make_submission(group=self.group1,
                                      submitted_files=files)

        for i in range(3):
            obj_build.make_submission(group=self.group2,
                                      submitted_files=files)

        expected_submission_count = (
            self.group1.submissions.count() + self.group2.submissions.count())
        expected_member_names = self.group1.member_names + self.group2.member_names
        self.assertEqual(2, ag_models.Group.objects.count())

        self.client.force_authenticate(self.admin)

        response = self.client.post(self.get_merge_url(self.group1, self.group2))
        self.assertEqual(status.HTTP_201_CREATED, response.status_code)

        self.assertEqual(1, ag_models.Group.objects.count())
        merged_group = ag_models.Group.objects.first()
        self.assertEqual(merged_group.to_dict(), response.data)
        self.assertCountEqual(expected_member_names, merged_group.member_names)

        self.assertEqual(expected_submission_count, merged_group.submissions.count())
        for submission in merged_group.submissions.all():
            for file_ in files:
                file_.seek(0)
                self.assertEqual(submission.get_file(file_.name).read(),
                                 file_.read())

    def test_non_admin_permission_denied(self):
        staff = obj_build.make_staff_user(self.course)
        student = obj_build.make_student_user(self.course)
        handgrader = obj_build.make_handgrader_user(self.course)
        guest = obj_build.make_user()
        for user in staff, student, guest, handgrader:
            with self.assert_queryset_count_unchanged(ag_models.Group.objects):
                self.client.force_authenticate(user)
                response = self.client.post(self.get_merge_url(self.group1, self.group2))

            self.assertEqual(status.HTTP_403_FORBIDDEN, response.status_code)

    def test_one_group_with_extension(self):
        extension_date = timezone.now()
        self.client.force_authenticate(self.admin)
        self.group1.validate_and_update(extended_due_date=extension_date)
        response = self.client.post(self.get_merge_url(self.group1, self.group2))
        self.assertEqual(status.HTTP_201_CREATED, response.status_code)
        self.assertEqual(response.data['extended_due_date'], extension_date)

    def test_both_have_extension(self):
        earlier_extension_date = timezone.now()
        later_extension_date = earlier_extension_date + timezone.timedelta(hours=1)
        self.group1.validate_and_update(extended_due_date=earlier_extension_date)
        self.group2.validate_and_update(extended_due_date=later_extension_date)
        self.client.force_authenticate(self.admin)
        response = self.client.post(self.get_merge_url(self.group1, self.group2))
        self.assertEqual(status.HTTP_201_CREATED, response.status_code)
        self.assertEqual(response.data['extended_due_date'], later_extension_date)

    def test_bonus_submission_merging(self) -> None:
        fewer_bonus_submissions = 1
        more_bonus_submissions = 3
        self.group1.validate_and_update(bonus_submissions_remaining=more_bonus_submissions)
        self.group2.validate_and_update(bonus_submissions_remaining=fewer_bonus_submissions)
        self.client.force_authenticate(self.admin)
        response = self.client.post(self.get_merge_url(self.group1, self.group2))
        self.assertEqual(status.HTTP_201_CREATED, response.status_code)
        self.assertEqual(response.data['bonus_submissions_remaining'], fewer_bonus_submissions)

    def test_late_day_merging(self) -> None:
        self.group1.late_days_used = {
            self.group1.member_names[0]: 1
        }
        self.group1.save()
        self.group2.late_days_used = {
            self.group2.member_names[0]: 2
        }
        self.group2.save()

        self.client.force_authenticate(self.admin)
        response = self.client.post(self.get_merge_url(self.group1, self.group2))
        self.assertEqual(status.HTTP_201_CREATED, response.status_code)
        self.assertEqual(response.data['late_days_used'], {
            self.group1.member_names[0]: 1,
            self.group2.member_names[0]: 2
        })

    def test_error_merge_staff_and_non_staff(self):
        staff_group = obj_build.make_group(
            project=self.project, members_role=obj_build.UserRole.staff)
        with self.assert_queryset_count_unchanged(ag_models.Group.objects):
            self.client.force_authenticate(self.admin)
            response = self.client.post(self.get_merge_url(self.group1, staff_group))

        self.assertEqual(status.HTTP_400_BAD_REQUEST, response.status_code)
        self.assertIn('members', response.data)

    def test_error_merge_student_and_guest(self):
        guest_group = obj_build.make_group(
            project=self.project, members_role=obj_build.UserRole.guest)
        with self.assert_queryset_count_unchanged(ag_models.Group.objects):
            self.client.force_authenticate(self.admin)
            response = self.client.post(self.get_merge_url(self.group1, guest_group))

        self.assertEqual(status.HTTP_400_BAD_REQUEST, response.status_code)
        self.assertIn('members', response.data)

    def test_query_param_pk_not_found(self):
        with self.assert_queryset_count_unchanged(ag_models.Group.objects):
            self.client.force_authenticate(self.admin)
            response = self.client.post(
                reverse('merge-groups', kwargs={'pk': self.group1.pk, 'other_group_pk': 9001}))

        self.assertEqual(status.HTTP_404_NOT_FOUND, response.status_code)

    def test_error_merge_groups_diff_projects(self):
        group_diff_proj = obj_build.make_group(
            project=obj_build.make_project(self.course),
            members_role=obj_build.UserRole.student
        )
        self.assertNotEqual(self.group1.project, group_diff_proj.project)
        with self.assert_queryset_count_unchanged(ag_models.Group.objects):
            self.client.force_authenticate(self.admin)
            response = self.client.post(self.get_merge_url(self.group1, group_diff_proj))

        self.assertEqual(status.HTTP_400_BAD_REQUEST, response.status_code)
        self.assertIn('groups', response.data)
        self.assertIn('project', response.data['groups'])

    def get_merge_url(self, group1, group2):
        return (reverse('merge-groups', kwargs={'pk': group1.pk, 'other_group_pk': group2.pk}))


class DeleteGroupTestCase(AGViewTestBase):
    def setUp(self):
        super().setUp()

        self.group = obj_build.make_group(num_members=5)
        self.course = self.group.project.course
        self.url = reverse('group-detail', kwargs={'pk': self.group.pk})
        self.client = APIClient()

    def test_admin_delete_group(self) -> None:
        original_member_names = self.group.member_names
        original_user_pks = {user.pk for user in self.group.members.all()}
        admin = obj_build.make_admin_user(self.course)
        self.client.force_authenticate(admin)
        response = self.client.delete(self.url)
        self.assertEqual(status.HTTP_204_NO_CONTENT, response.status_code)

        self.group = ag_models.Group.objects.get(pk=self.group.pk)
        new_user_pks = {user.pk for user in self.group.members.all()}
        self.assertTrue(original_user_pks.isdisjoint(new_user_pks))
        for index, original_name in enumerate(original_member_names):
            self.assertEqual(
                f'~deleted_{self.group.pk}_' + original_name, self.group.member_names[index])

    def test_non_admin_delete_group_permission_denied(self) -> None:
        original_member_names = self.group.member_names
        staff = obj_build.make_staff_user(self.course)
        self.client.force_authenticate(staff)
        response = self.client.delete(self.url)
        self.assertEqual(status.HTTP_403_FORBIDDEN, response.status_code)

        self.group = ag_models.Group.objects.get(pk=self.group.pk)
        self.assertEqual(original_member_names, self.group.member_names)
