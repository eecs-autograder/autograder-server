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
import autograder.rest_api.serializers as ag_serializers
import autograder.rest_api.tests.test_views.ag_view_test_base as test_impls
import autograder.rest_api.tests.test_views.common_generic_data as test_data
import autograder.utils.testing.model_obj_builders as obj_build
from autograder.rest_api.tests.test_views.ag_view_test_base import AGViewTestBase
from autograder.utils.testing import UnitTestBase


class _GroupsSetUp(test_data.Client, test_data.Project):
    pass


# TODO: When removing common_generic_data module, consider adding more tests for
# guests and allowed domain.


class SortedListGroupsTestCase(test_data.Client, UnitTestBase):
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


class ListGroupsTestCase(_GroupsSetUp,
                         test_impls.ListObjectsTest,
                         test_impls.PermissionDeniedGetTest,
                         UnitTestBase):
    def test_admin_list_groups(self):
        for project in self.all_projects:
            self.do_list_objects_test(
                self.client, self.admin, self.get_groups_url(project),
                self.build_groups(project), check_order=True)

    def test_staff_list_groups(self):
        for project in self.all_projects:
            self.do_list_objects_test(
                self.client, self.staff, self.get_groups_url(project),
                self.build_groups(project), check_order=True)

    def test_enrolled_list_groups(self):
        for project in self.all_projects:
            self.build_groups(project)
            self.do_permission_denied_get_test(
                self.client, self.enrolled, self.get_groups_url(project))

    def test_handgrader_list_groups(self):
        for project in self.all_projects:
            self.do_list_objects_test(self.client, self.handgrader, self.get_groups_url(project),
                                      self.build_groups(project))

    def test_other_list_groups(self):
        for project in self.all_projects:
            self.build_groups(project)
            self.do_permission_denied_get_test(
                self.client, self.enrolled, self.get_groups_url(project))

    def test_prefetching_doesnt_skew_num_submissions_and_num_submissions_towards_limit(self):
        self.maxDiff = None
        group1 = obj_build.make_group(project=self.visible_public_project)
        group1_yesterday_submission = obj_build.make_submission(
            group=group1,
            timestamp=timezone.now() - datetime.timedelta(days=1))
        group1_not_towards_limit_submission = obj_build.make_submission(
            group=group1,
            count_towards_daily_limit=False)
        group1_towards_limit_submission = obj_build.make_submission(group=group1)

        group1.refresh_from_db()
        self.assertEqual(3, group1.num_submissions)
        self.assertEqual(1, group1.num_submits_towards_limit)

        group2 = obj_build.make_group(project=self.visible_public_project)
        group2_yesterday_submission = obj_build.make_submission(
            group=group2,
            timestamp=timezone.now() - datetime.timedelta(days=1))
        group2_yesterday_submission2 = obj_build.make_submission(
            group=group2,
            timestamp=timezone.now() - datetime.timedelta(days=1))
        group2_not_towards_limit_submission = obj_build.make_submission(
            group=group2,
            count_towards_daily_limit=False)
        group2_towards_limit_submission = obj_build.make_submission(group=group2)

        group2.refresh_from_db()
        self.assertEqual(4, group2.num_submissions)
        self.assertEqual(1, group2.num_submits_towards_limit)

        self.client.force_authenticate(self.admin)
        response = self.client.get(self.get_groups_url(self.visible_public_project))
        self.assertEqual(status.HTTP_200_OK, response.status_code)

        self.assertCountEqual([group1.to_dict(), group2.to_dict()], response.data)

    def build_groups(self, project):
        project.validate_and_update(
            guests_can_submit=True)
        for user in self.admin, self.staff, self.enrolled, self.nobody:
            ag_models.Group.objects.validate_and_create(
                project=project, members=[user])

        serialized_groups = ag_serializers.SubmissionGroupSerializer(
            project.groups.all(), many=True).data
        self.assertEqual(4, len(serialized_groups))
        return serialized_groups


class CreateGroupTestCase(_GroupsSetUp,
                          test_impls.CreateObjectTest,
                          test_impls.CreateObjectInvalidArgsTest,
                          test_impls.PermissionDeniedCreateTest,
                          UnitTestBase):
    def setUp(self):
        super().setUp()
        self.url = self.get_groups_url(self.project)

    def test_admin_create_enrolled_group(self):
        args = {'member_names': self.get_legal_member_names()}
        self.do_create_object_test(self.project.groups,
                                   self.client, self.admin, self.url, args)

    def test_admin_create_non_enrolled_group(self):
        self.project.validate_and_update(
            guests_can_submit=True)
        args = {'member_names': ['not_enrolled1', 'not_enrolled2']}
        self.do_create_object_test(self.project.groups,
                                   self.client, self.admin, self.url, args)

    def test_admin_create_group_override_size(self):
        self.project.validate_and_update(max_group_size=1)
        args = {'member_names': self.get_legal_member_names()}

        self.do_create_object_test(self.project.groups,
                                   self.client, self.admin, self.url, args)

    def test_admin_create_group_error_invalid_members(self):
        args = {'member_names': [self.enrolled.username, self.nobody.username]}
        self.do_invalid_create_object_test(
            self.project.groups, self.client, self.admin, self.url,
            args)

    def test_admin_create_group_error_non_allowed_domain_guest(self):
        self.project.course.validate_and_update(allowed_guest_domain='@llama.edu')
        self.project.validate_and_update(guests_can_submit=True)
        allowed_guest = obj_build.make_allowed_domain_guest_user(self.course)
        non_allowed_guest = obj_build.make_user()

        args = {'member_names': [allowed_guest.username, non_allowed_guest.username]}
        self.do_invalid_create_object_test(
            self.project.groups, self.client, self.admin, self.url, args)

    def test_admin_create_group_missing_member_names(self):
        self.do_invalid_create_object_test(
            self.project.groups, self.client, self.admin, self.url, {})

    def test_handgrader_create_group_permission_denied(self):
        other_handgrader = obj_build.make_handgrader_user(self.course)
        for project in self.all_projects:
            self.do_permission_denied_create_test(
                project.groups, self.client, self.handgrader,
                self.get_groups_url(project), {'member_names': [other_handgrader.username]})

    def test_other_create_group_permission_denied(self):
        args = {'member_names': self.get_legal_member_names()}
        for user in (self.staff, self.enrolled, self.handgrader, self.get_legal_members()[0],
                     self.nobody):
            self.do_permission_denied_create_test(
                self.project.groups, self.client, user,
                self.get_groups_url(self.project), args)

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


class CreateSoloGroupTestCase(_GroupsSetUp, test_impls.CreateObjectTest,
                              UnitTestBase):
    def get_solo_group_url(self, project):
        return reverse('solo_group', kwargs={'project_pk': project.pk})

    def test_create_solo_group_min_size_one(self):
        for user in self.admin, self.staff, self.enrolled, self.nobody:
            response = self.do_create_object_test(
                self.visible_public_project.groups,
                self.client, user,
                self.get_solo_group_url(self.visible_public_project), {},
                check_data=False)
            self.assertCountEqual([user.username],
                                  response.data['member_names'])

    def test_student_create_solo_group_visible_private_project(self):
        response = self.do_create_object_test(
            self.visible_private_project.groups,
            self.client, self.enrolled,
            self.get_solo_group_url(self.visible_private_project), {},
            check_data=False)
        self.assertCountEqual([self.enrolled.username],
                              response.data['member_names'])

    def test_student_create_solo_group_min_size_not_one_invalid(self):
        self.visible_public_project.validate_and_update(
            min_group_size=2, max_group_size=2)
        for user in self.enrolled, self.nobody:
            self.do_invalid_create_object_test(
                self.visible_public_project.groups,
                self.client, user,
                self.get_solo_group_url(self.visible_public_project), {})

    def test_staff_create_solo_group_project_hidden_allowed(self):
        response = self.do_create_object_test(
            self.hidden_private_project.groups,
            self.client, self.staff,
            self.get_solo_group_url(self.hidden_private_project), {},
            check_data=False)
        self.assertCountEqual([self.staff.username],
                              response.data['member_names'])

    def test_staff_create_solo_group_min_size_not_one_allowed(self):
        self.project.validate_and_update(min_group_size=2, max_group_size=2)
        response = self.do_create_object_test(
            self.project.groups,
            self.client, self.staff,
            self.get_solo_group_url(self.project), {},
            check_data=False)
        self.assertCountEqual([self.staff.username],
                              response.data['member_names'])

    def test_handgrader_create_solo_group_permission_denied(self):
        for project in self.visible_private_project, self.hidden_private_project:
            self.do_permission_denied_create_test(project.groups, self.client,
                                                  self.handgrader,
                                                  self.get_solo_group_url(project), {})

    def test_handgrader_create_solo_group_when_enrolled(self):
        for project in self.visible_projects:
            project.course.students.add(self.handgrader)
            self.do_create_object_test(project.groups, self.client,
                                       self.handgrader,
                                       self.get_solo_group_url(project), {})

    def test_student_create_solo_group_project_hidden_permission_denied(self):
        for user in self.enrolled, self.nobody:
            self.do_permission_denied_create_test(
                self.hidden_public_project.groups,
                self.client, user,
                self.get_solo_group_url(self.hidden_public_project), {})

    def test_non_enrolled_create_solo_group_project_private_permission_denied(self):
        self.do_permission_denied_create_test(
            self.visible_private_project.groups,
            self.client, self.nobody,
            self.get_solo_group_url(self.visible_private_project), {})


class RetrieveGroupTestCase(test_data.Client,
                            test_data.Project,
                            test_data.Group,
                            test_impls.GetObjectTest,
                            UnitTestBase):

    def test_admin_or_staff_get_group(self):
        for project in self.all_projects:
            for group in self.at_least_enrolled_groups(project):
                for user in self.admin, self.staff:
                    self.do_get_object_test(
                        self.client, user, self.group_url(group),
                        group.to_dict())

        for project in self.public_projects:
            group = self.non_enrolled_group(project)
            for user in self.admin, self.staff:
                self.do_get_object_test(
                    self.client, user, self.group_url(group), group.to_dict())

    def test_enrolled_get_group(self):
        for project in self.visible_projects:
            group = self.enrolled_group(project)
            for user in group.members.all():
                self.do_get_object_test(
                    self.client, user, self.group_url(group), group.to_dict())

    def test_non_enrolled_get_group(self):
        group = self.non_enrolled_group(self.visible_public_project)
        for user in group.members.all():
            self.do_get_object_test(
                self.client, user, self.group_url(group), group.to_dict())

    def test_non_member_view_group_permission_denied(self):
        group = self.enrolled_group(self.visible_public_project)
        non_member = self.clone_user(self.enrolled)
        for user in non_member, self.nobody:
            self.do_permission_denied_get_test(
                self.client, user, self.group_url(group))

    def test_enrolled_view_group_project_hidden_permission_denied(self):
        for project in self.hidden_projects:
            group = self.enrolled_group(project)
            self.do_permission_denied_get_test(
                self.client, self.enrolled, self.group_url(group))

    def test_non_enrolled_view_group_project_hidden_permission_denied(self):
        group = self.non_enrolled_group(self.hidden_public_project)
        self.do_permission_denied_get_test(
            self.client, self.nobody, self.group_url(group))

    def test_non_enrolled_view_group_project_private_permission_denied(self):
        group = self.non_enrolled_group(self.visible_public_project)
        self.visible_public_project.validate_and_update(
            guests_can_submit=False)
        self.do_permission_denied_get_test(
            self.client, self.nobody, self.group_url(group))

    def test_handgrader_get_group_permission_denied(self):
        for project in self.all_projects:
            for group in self.at_least_enrolled_groups(project):
                self.do_permission_denied_get_test(self.client, self.handgrader,
                                                   self.group_url(group))

        for project in self.public_projects:
            group = self.non_enrolled_group(project)
            self.do_permission_denied_get_test(self.client, self.handgrader, self.group_url(group))

    def test_prefetching_doesnt_skew_num_submissions_and_num_submissions_towards_limit(self):
        group = obj_build.make_group(project=self.visible_public_project)
        yesterday_submission = obj_build.make_submission(
            group=group,
            timestamp=timezone.now() - datetime.timedelta(days=1))
        not_towards_limit_submission = obj_build.make_submission(
            group=group,
            count_towards_daily_limit=False)
        towards_limit_submission = obj_build.make_submission(group=group)

        group.refresh_from_db()
        self.assertEqual(3, group.num_submissions)
        self.assertEqual(1, group.num_submits_towards_limit)

        self.client.force_authenticate(self.admin)
        response = self.client.get(self.group_url(group))
        self.assertEqual(status.HTTP_200_OK, response.status_code)
        self.assertEqual(3, response.data['num_submissions'])
        self.assertEqual(1, response.data['num_submits_towards_limit'])


class UpdateGroupTestCase(test_data.Client,
                          test_data.Project,
                          test_data.Group,
                          test_impls.UpdateObjectTest,
                          UnitTestBase):

    def setUp(self):
        super().setUp()
        self.new_due_date = timezone.now().replace(microsecond=0)

    def get_names(self, users):
        return [user.username for user in users]

    def test_admin_update_admin_and_staff_group_members(self):
        for project in self.all_projects:
            group = self.staff_group(project)
            new_members = list(group.members.all())[:-1] + [self.clone_user(self.admin)]
            self.do_patch_object_test(
                group, self.client, self.admin, self.group_url(group),
                {'member_names': self.get_names(new_members)})

    def test_admin_update_enrolled_group_members(self):
        for project in self.all_projects:
            group = self.enrolled_group(project)
            new_members = list(group.members.all())[:-1] + [self.clone_user(self.enrolled)]
            self.do_patch_object_test(
                group, self.client, self.admin, self.group_url(group),
                {'member_names': self.get_names(new_members)})

    def test_admin_update_non_enrolled_group_members(self):
        for project in self.public_projects:
            group = self.non_enrolled_group(project)
            new_members = self.get_names(
                list(group.members.all())[:-1]) + ['stove']
            self.do_patch_object_test(
                group, self.client, self.admin, self.group_url(group),
                {'member_names': new_members})

    def test_admin_update_group_override_size(self):
        for project in self.all_projects:
            group = self.enrolled_group(project)
            new_members = list(group.members.all()) + [self.clone_user(self.enrolled)]
            self.assertGreater(len(new_members), project.max_group_size)
            self.do_patch_object_test(
                group, self.client, self.admin, self.group_url(group),
                {'member_names': self.get_names(new_members)})

    def test_admin_update_group_extension(self):
        for project in self.all_projects:
            group = self.enrolled_group(project)
            # give and revoke extension
            self.do_patch_object_test(
                group, self.client, self.admin, self.group_url(group),
                {'extended_due_date': self.new_due_date})
            self.do_patch_object_test(
                group, self.client, self.admin, self.group_url(group),
                {'extended_due_date': None})

        for project in self.public_projects:
            group = self.non_enrolled_group(project)
            self.do_patch_object_test(
                group, self.client, self.admin, self.group_url(group),
                {'extended_due_date': self.new_due_date})
            self.do_patch_object_test(
                group, self.client, self.admin, self.group_url(group),
                {'extended_due_date': None})

    def test_admin_update_group_invalid_members(self):
        for project in self.all_projects:
            group = self.enrolled_group(project)
            new_members = self.get_names(
                list(group.members.all())[:-1]) + ['stove']
            response = self.do_patch_object_invalid_args_test(
                group, self.client, self.admin, self.group_url(group),
                {'member_names': new_members})
            self.assertIn('members', response.data)

    def test_admin_update_group_error_non_allowed_domain_guest(self):
        self.course.validate_and_update(allowed_guest_domain='@llama.edu')
        self.project.validate_and_update(guests_can_submit=True)
        allowed_guest = obj_build.make_allowed_domain_guest_user(self.course)

        group = ag_models.Group.objects.validate_and_create(
            members=[allowed_guest], project=self.project, check_group_size_limits=False
        )

        non_allowed_guest = obj_build.make_user()

        response = self.do_patch_object_invalid_args_test(
            group, self.client, self.admin, self.group_url(group),
            {'member_names': [allowed_guest.username, non_allowed_guest.username]})
        self.assertIn('members', response.data)

    def test_admin_update_group_bad_date(self):
        group = self.enrolled_group(self.visible_public_project)
        response = self.do_patch_object_invalid_args_test(
            group, self.client, self.admin, self.group_url(group),
            {'extended_due_date': 'not a date'})
        self.assertIn('extended_due_date', response.data)

    def test_other_update_group_permission_denied(self):
        for group in (self.staff_group(self.visible_public_project),
                      self.enrolled_group(self.visible_public_project),
                      self.non_enrolled_group(self.visible_public_project)):
            for user in self.staff, self.enrolled, self.nobody, self.handgrader:
                self.do_patch_object_permission_denied_test(
                    group, self.client, user, self.group_url(group),
                    {'extended_due_date': self.new_due_date})


class MergeGroupsTestCase(test_data.Client,
                          test_data.Project,
                          test_data.Submission,
                          test_impls.PermissionDeniedGetTest,
                          UnitTestBase):
    def setUp(self):
        super().setUp()
        self.group1 = obj_build.build_group(
            group_kwargs={'project': self.visible_public_project})
        self.group2 = obj_build.build_group(
            group_kwargs={'project': self.visible_public_project})
        self.original_num_groups = 2
        self.assertEqual(self.original_num_groups, ag_models.Group.objects.count())

    def test_normal_merge(self):
        files = []
        for i in range(2):
            file_name = 'whatever_you_want' + str(i)
            ag_models.ExpectedStudentFile.objects.create(
                pattern=file_name, project=self.visible_public_project)
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
        for user in self.staff, self.enrolled, self.nobody, self.handgrader:
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
        self.client.force_authenticate(self.admin)
        self.group1.validate_and_update(extended_due_date=earlier_extension_date)
        self.group2.validate_and_update(extended_due_date=later_extension_date)
        response = self.client.post(self.get_merge_url(self.group1, self.group2))
        self.assertEqual(status.HTTP_201_CREATED, response.status_code)
        self.assertEqual(response.data['extended_due_date'], later_extension_date)

    def test_error_merge_staff_and_non_staff(self):
        staff_group = self.staff_group(self.group1.project)
        with self.assert_queryset_count_unchanged(ag_models.Group.objects):
            self.client.force_authenticate(self.admin)
            response = self.client.post(self.get_merge_url(self.group1, staff_group))

        self.assertEqual(status.HTTP_400_BAD_REQUEST, response.status_code)
        self.assertIn('members', response.data)

    def test_error_merge_enrolled_and_non_enrolled(self):
        non_enrolled_group = self.non_enrolled_group(self.group1.project)
        with self.assert_queryset_count_unchanged(ag_models.Group.objects):
            self.client.force_authenticate(self.admin)
            response = self.client.post(self.get_merge_url(self.group1, non_enrolled_group))

        self.assertEqual(status.HTTP_400_BAD_REQUEST, response.status_code)
        self.assertIn('members', response.data)

    def test_missing_query_param(self):
        with self.assert_queryset_count_unchanged(ag_models.Group.objects):
            self.client.force_authenticate(self.admin)
            response = self.client.post(reverse('group-merge-with',
                                                kwargs={'pk': self.group1.pk}))

        self.assertEqual(status.HTTP_400_BAD_REQUEST, response.status_code)
        self.assertIn('other_group_pk', response.data)

    def test_query_param_pk_not_found(self):
        with self.assert_queryset_count_unchanged(ag_models.Group.objects):
            self.client.force_authenticate(self.admin)
            response = self.client.post(
                reverse('group-merge-with', kwargs={'pk': self.group1.pk})
                + '?other_group_pk=' + str(9001))

        self.assertEqual(status.HTTP_404_NOT_FOUND, response.status_code)

    def test_error_merge_groups_diff_projects(self):
        group_diff_proj = obj_build.build_group(
            group_kwargs={'project': self.visible_private_project})
        self.assertNotEqual(self.group1.project, group_diff_proj.project)
        with self.assert_queryset_count_unchanged(ag_models.Group.objects):
            self.client.force_authenticate(self.admin)
            response = self.client.post(self.get_merge_url(self.group1, group_diff_proj))

        self.assertEqual(status.HTTP_400_BAD_REQUEST, response.status_code)
        self.assertIn('groups', response.data)

    def get_merge_url(self, group1, group2):
        return (reverse('group-merge-with', kwargs={'pk': group1.pk})
                + '?other_group_pk=' + str(group2.pk))


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
