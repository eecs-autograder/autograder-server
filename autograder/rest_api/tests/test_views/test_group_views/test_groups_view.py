from typing import List

from django.core.urlresolvers import reverse
from django.contrib.auth.models import User

import autograder.core.models as ag_models
import autograder.rest_api.serializers as ag_serializers

from autograder.utils.testing import UnitTestBase
import autograder.utils.testing.model_obj_builders as obj_build
import autograder.rest_api.tests.test_views.common_generic_data as test_data
import autograder.rest_api.tests.test_views.common_test_impls as test_impls


class _GroupsSetUp(test_data.Client, test_data.Project):
    pass


class SortedListGroupsTestCase(test_data.Client, UnitTestBase):
    def test_groups_sorted_by_least_alphabetical_username(self):
        self.maxDiff = None

        project = obj_build.make_project(max_group_size=3, guests_can_submit=True)
        [admin] = obj_build.make_admin_users(project.course, 1)

        group1_user1 = User.objects.create(username='fred')
        group1 = ag_models.SubmissionGroup.objects.validate_and_create(
            members=[group1_user1], project=project)

        group2_user1 = User.objects.create(username='steve')
        group2_user2 = User.objects.create(username='anna')
        group2 = ag_models.SubmissionGroup.objects.validate_and_create(
            members=[group2_user1, group2_user2], project=project)

        group3_user1 = User.objects.create(username='georgina')
        group3_user2 = User.objects.create(username='joe')
        group3_user3 = User.objects.create(username='belinda')
        group3 = ag_models.SubmissionGroup.objects.validate_and_create(
            members=[group3_user1, group3_user2, group3_user3], project=project)

        expected = [group2.to_dict(), group3.to_dict(), group1.to_dict()]  # type: List[dict]
        for group_dict in expected:
            group_dict['member_names'] = list(sorted(group_dict['member_names']))

        self.client.force_authenticate(admin)
        response = self.client.get(reverse('submission_groups', kwargs={'project_pk': project.pk}))
        self.assertEqual(expected, response.data)


class ListGroupsTestCase(_GroupsSetUp,
                         test_impls.ListObjectsTest,
                         test_impls.PermissionDeniedGetTest,
                         UnitTestBase):
    def test_admin_list_groups(self):
        for project in self.all_projects:
            self.do_list_objects_test(
                self.client, self.admin, self.get_groups_url(project),
                self.build_groups(project))

    def test_staff_list_groups(self):
        for project in self.all_projects:
            self.do_list_objects_test(
                self.client, self.staff, self.get_groups_url(project),
                self.build_groups(project))

    def test_enrolled_list_groups(self):
        for project in self.all_projects:
            self.build_groups(project)
            self.do_permission_denied_get_test(
                self.client, self.enrolled, self.get_groups_url(project))

    def test_handgrader_list_groups(self):
        for project in self.all_projects:
            self.do_list_objects_test(
                self.client, self.handgrader, self.get_groups_url(project),
                self.build_groups(project))

    def test_other_list_groups(self):
        for project in self.all_projects:
            self.build_groups(project)
            self.do_permission_denied_get_test(
                self.client, self.enrolled, self.get_groups_url(project))

    def build_groups(self, project):
        project.validate_and_update(
            guests_can_submit=True)
        for user in self.admin, self.staff, self.enrolled, self.nobody:
            ag_models.SubmissionGroup.objects.validate_and_create(
                project=project, members=[user])

        serialized_groups = ag_serializers.SubmissionGroupSerializer(
            project.submission_groups.all(), many=True).data
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
        self.do_create_object_test(self.project.submission_groups,
                                   self.client, self.admin, self.url, args)

    def test_admin_create_non_enrolled_group(self):
        self.project.validate_and_update(
            guests_can_submit=True)
        args = {'member_names': ['not_enrolled1', 'not_enrolled2']}
        self.do_create_object_test(self.project.submission_groups,
                                   self.client, self.admin, self.url, args)

    def test_admin_create_group_override_size(self):
        self.project.validate_and_update(max_group_size=1)
        args = {'member_names': self.get_legal_member_names()}

        self.do_create_object_test(self.project.submission_groups,
                                   self.client, self.admin, self.url, args)

    def test_admin_create_group_error_invalid_members(self):
        args = {'member_names': [self.enrolled.username, self.nobody.username]}
        self.do_invalid_create_object_test(
            self.project.submission_groups, self.client, self.admin, self.url,
            args)

    def test_other_create_group_permission_denied(self):
        args = {'member_names': self.get_legal_member_names()}
        for user in (self.staff, self.enrolled, self.handgrader, self.get_legal_members()[0],
                     self.nobody):
            self.do_permission_denied_create_test(
                self.project.submission_groups, self.client, user,
                self.get_groups_url(self.project), args)

    # def test_pending_invitations_deleted_after_group_create(self):
    #     self.fail()

    def get_legal_members(self):
        if hasattr(self, '_legal_members'):
            return self._legal_members

        self.project.validate_and_update(max_group_size=3)
        self._legal_members = obj_build.create_dummy_users(2)
        self.project.course.enrolled_students.add(*self._legal_members)
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
                self.visible_public_project.submission_groups,
                self.client, user,
                self.get_solo_group_url(self.visible_public_project), {},
                check_data=False)
            self.assertCountEqual([user.username],
                                  response.data['member_names'])

    def test_student_create_solo_group_visible_private_project(self):
        response = self.do_create_object_test(
            self.visible_private_project.submission_groups,
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
                self.visible_public_project.submission_groups,
                self.client, user,
                self.get_solo_group_url(self.visible_public_project), {})

    def test_staff_create_solo_group_project_hidden_allowed(self):
        response = self.do_create_object_test(
            self.hidden_private_project.submission_groups,
            self.client, self.staff,
            self.get_solo_group_url(self.hidden_private_project), {},
            check_data=False)
        self.assertCountEqual([self.staff.username],
                              response.data['member_names'])

    def test_staff_create_solo_group_min_size_not_one_allowed(self):
        self.project.validate_and_update(min_group_size=2, max_group_size=2)
        response = self.do_create_object_test(
            self.project.submission_groups,
            self.client, self.staff,
            self.get_solo_group_url(self.project), {},
            check_data=False)
        self.assertCountEqual([self.staff.username],
                              response.data['member_names'])

    def test_student_create_solo_group_project_hidden_permission_denied(self):
        for user in self.enrolled, self.nobody, self.handgrader:
            self.do_permission_denied_create_test(
                self.hidden_public_project.submission_groups,
                self.client, user,
                self.get_solo_group_url(self.hidden_public_project), {})

    def test_non_enrolled_create_solo_group_project_private_permission_denied(self):
        for user in self.nobody, self.handgrader:
            self.do_permission_denied_create_test(
                self.visible_private_project.submission_groups,
                self.client, user,
                self.get_solo_group_url(self.visible_private_project), {})
