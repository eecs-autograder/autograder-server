from rest_framework import status

import autograder.core.models as ag_models
import autograder.rest_api.serializers as ag_serializers

from autograder.core.tests.temporary_filesystem_test_case import (
    TemporaryFilesystemTestCase)
import autograder.core.tests.dummy_object_utils as obj_ut
import autograder.rest_api.tests.test_views.common_generic_data as test_data
import autograder.rest_api.tests.test_views.common_test_impls as test_impls


class _GroupsSetUp(test_data.Client, test_data.Project):
    pass


class ListGroupsTestCase(_GroupsSetUp,
                         test_impls.ListObjectsTest,
                         test_impls.PermissionDeniedGetTest,
                         TemporaryFilesystemTestCase):
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

    def test_other_list_groups(self):
        for project in self.all_projects:
            self.build_groups(project)
            self.do_permission_denied_get_test(
                self.client, self.enrolled, self.get_groups_url(project))

    def build_groups(self, project):
        project.validate_and_update(
            allow_submissions_from_non_enrolled_students=True)
        for user in self.admin, self.staff, self.enrolled, self.nobody:
            ag_models.SubmissionGroup.objects.validate_and_create(
                project=project, members=[user])

        serialized_groups = ag_serializers.SubmissionGroupSerializer(
            project.submission_groups.all(), many=True).data
        self.assertEqual(4, len(serialized_groups))
        return serialized_groups


class CreateGroupTestCase(_GroupsSetUp,
                          test_impls.PermissionDeniedCreateTest,
                          TemporaryFilesystemTestCase):
    def setUp(self):
        super().setUp()
        self.url = self.get_groups_url(self.project)

    def test_admin_create_group(self):
        self.assertEqual(0, self.project.submission_groups.count())
        args = {'members': self.get_legal_member_pks()}

        self.client.force_authenticate(self.admin)
        response = self.client.post(self.url, args)
        self.assertEqual(status.HTTP_201_CREATED, response.status_code)

        self.assertEqual(1, self.project.submission_groups.count())
        loaded = self.project.submission_groups.first()
        self.assertCountEqual(self.get_legal_members(), loaded.members.all())

    def test_admin_create_group_override_size(self):
        self.project.validate_and_update(max_group_size=1)

        self.assertEqual(0, self.project.submission_groups.count())
        args = {'members': self.get_legal_member_pks()}

        self.client.force_authenticate(self.admin)
        response = self.client.post(self.url, args)
        self.assertEqual(status.HTTP_201_CREATED, response.status_code)

        self.assertEqual(1, self.project.submission_groups.count())
        loaded = self.project.submission_groups.first()
        self.assertCountEqual(self.get_legal_members(), loaded.members.all())

    def test_admin_create_group_error_invalid_members(self):
        self.assertEqual(0, self.project.submission_groups.count())
        args = {'members': [self.enrolled.pk, self.nobody.pk]}
        self.client.force_authenticate(self.admin)
        response = self.client.post(self.url, args)
        self.assertEqual(status.HTTP_400_BAD_REQUEST, response.status_code)
        self.assertEqual(0, self.project.submission_groups.count())

    def test_other_create_group_permission_denied(self):
        args = {'members': self.get_legal_member_pks()}
        for user in (self.staff, self.enrolled, self.get_legal_members()[0],
                     self.nobody):
            self.do_permission_denied_create_test(
                self.project.submission_groups, self.client, user,
                self.get_groups_url(self.project), args)

    def get_legal_members(self):
        if hasattr(self, '_legal_members'):
            return self._legal_members

        self.project.validate_and_update(max_group_size=3)
        self._legal_members = obj_ut.create_dummy_users(2)
        self.project.course.enrolled_students.add(*self._legal_members)
        return self._legal_members

    def get_legal_member_pks(self):
        members = self.get_legal_members()
        return [member.pk for member in members]
