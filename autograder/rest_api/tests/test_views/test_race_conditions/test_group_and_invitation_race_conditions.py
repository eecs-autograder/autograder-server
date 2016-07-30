from rest_framework import status
from rest_framework.test import APIClient

import autograder.core.models as ag_models

from autograder.core.tests.temporary_filesystem_test_case import (
    TemporaryFilesystemTestCase)
import autograder.core.tests.dummy_object_utils as obj_ut
import autograder.rest_api.tests.test_views.common_generic_data as test_data

from .sleeper_subtest import sleeper_subtest

from autograder.rest_api.views.project_views.project_groups import (
    ProjectGroupsViewSet)
from autograder.rest_api.views.group_views.group_view import GroupViewset


class RaceConditionTestCase(test_data.Client,
                            test_data.Project,
                            test_data.Group,
                            TemporaryFilesystemTestCase):
    def test_create_group_and_invitation_with_invitor_in_both(self):
        self.visible_public_project.validate_and_update(max_group_size=4)
        project_id = self.visible_public_project.pk
        invitor = obj_ut.create_dummy_user()
        path = ('autograder.rest_api.views.project_views.project_groups'
                '.ProjectGroupsViewSet.serializer_class')

        @sleeper_subtest(path, wraps=ProjectGroupsViewSet.serializer_class)
        def create_group(project_id):
            project = ag_models.Project.objects.get(pk=project_id)
            client = APIClient()
            client.force_authenticate(self.admin)
            response = client.post(
                self.get_groups_url(project),
                {'member_names': [invitor.username, 'this_one']})
            self.assertEqual(status.HTTP_201_CREATED, response.status_code)
            self.assertEqual(1, ag_models.SubmissionGroup.objects.count())

        subtest = create_group(project_id)
        self.client.force_authenticate(invitor)
        response = self.client.post(
            self.get_invitations_url(self.visible_public_project),
            {'invited_usernames': ['other_one']})
        subtest.join()
        self.assertEqual(1, ag_models.SubmissionGroup.objects.count())
        self.assertEqual(status.HTTP_400_BAD_REQUEST, response.status_code)

    def test_create_group_and_invitation_with_member_in_both(self):
        self.visible_public_project.validate_and_update(max_group_size=4)
        project_id = self.visible_public_project.pk
        invitor = obj_ut.create_dummy_user()
        overlap_username = 'steve'
        path = ('autograder.rest_api.views.project_views.project_groups'
                '.ProjectGroupsViewSet.serializer_class')

        @sleeper_subtest(path, wraps=ProjectGroupsViewSet.serializer_class)
        def do_request_and_wait(project_id):
            project = ag_models.Project.objects.get(pk=project_id)
            client = APIClient()
            client.force_authenticate(self.admin)
            response = client.post(
                self.get_groups_url(project),
                {'member_names': [overlap_username, 'this_one']})
            self.assertEqual(status.HTTP_201_CREATED, response.status_code)
            self.assertEqual(1, ag_models.SubmissionGroup.objects.count())

        subtest = do_request_and_wait(project_id)
        self.client.force_authenticate(invitor)
        response = self.client.post(
            self.get_invitations_url(self.visible_public_project),
            {'invited_usernames': [overlap_username]})
        subtest.join()
        self.assertEqual(status.HTTP_400_BAD_REQUEST, response.status_code)
        self.assertEqual(1, ag_models.SubmissionGroup.objects.count())

    def test_create_groups_with_member_overlap(self):
        self.visible_public_project.validate_and_update(max_group_size=4)
        project_id = self.visible_public_project.pk
        overlap_username = 'stave'
        path = ('autograder.rest_api.views.project_views.project_groups'
                '.ProjectGroupsViewSet.serializer_class')

        @sleeper_subtest(path, wraps=ProjectGroupsViewSet.serializer_class)
        def do_request_and_wait(project_id):
            project = ag_models.Project.objects.get(pk=project_id)
            client = APIClient()
            client.force_authenticate(self.admin)
            response = client.post(
                self.get_groups_url(project),
                {'member_names': [overlap_username, 'this_one']})
            self.assertEqual(status.HTTP_201_CREATED, response.status_code)
            self.assertEqual(1, ag_models.SubmissionGroup.objects.count())

        subtest = do_request_and_wait(project_id)
        self.client.force_authenticate(self.admin)
        response = self.client.post(
            self.get_groups_url(self.visible_public_project),
            {'member_names': [overlap_username, 'other_one']})
        subtest.join()
        self.assertEqual(status.HTTP_400_BAD_REQUEST, response.status_code)
        self.assertEqual(1, ag_models.SubmissionGroup.objects.count())

    def test_update_groups_with_member_overlap(self):
        self.visible_public_project.validate_and_update(max_group_size=4)
        first_group = self.admin_group(self.visible_public_project)
        second_group = self.staff_group(self.visible_public_project)
        overlap_member = self.clone_user(self.staff)
        path = ('autograder.rest_api.views.group_views'
                '.group_view.GroupViewset.serializer_class')

        @sleeper_subtest(path, wraps=GroupViewset.serializer_class)
        def update_first_group():
            client = APIClient()
            client.force_authenticate(self.admin)
            member_names = [overlap_member.username] + first_group.member_names
            response = client.patch(self.group_url(first_group),
                                    {'member_names': member_names})
            self.assertEqual(status.HTTP_200_OK, response.status_code)
            self.assertCountEqual(member_names, first_group.member_names)

        subtest = update_first_group()
        self.client.force_authenticate(self.admin)
        member_names = ([overlap_member.username] + second_group.member_names)
        response = self.client.patch(self.group_url(second_group),
                                     {'member_names': member_names})
        subtest.join()
        self.assertEqual(status.HTTP_400_BAD_REQUEST, response.status_code)
        second_group.refresh_from_db()
        self.assertNotIn(overlap_member.username, second_group.member_names)

    def test_update_groups_with_multiple_overlap_no_deadlock(self):
        self.fail()

    def test_create_and_update_groups_with_member_overlap(self):
        self.project.validate_and_update(max_group_size=4)
        group = self.admin_group(self.project)
        overlap_member = self.clone_user(self.staff)
        new_member_names = group.member_names + [overlap_member.username]
        path = ('autograder.rest_api.views.project_views.project_groups'
                '.ProjectGroupsViewSet.serializer_class')
        self.assertEqual(1, ag_models.SubmissionGroup.objects.count())

        @sleeper_subtest(path, wraps=ProjectGroupsViewSet.serializer_class)
        def create_group():
            client = APIClient()
            client.force_authenticate(self.admin)
            member_names = [overlap_member.username, self.staff.username]
            response = client.post(self.get_groups_url(self.project),
                                   {'member_names': member_names})
            self.assertEqual(status.HTTP_201_CREATED, response.status_code)
            self.assertEqual(2, ag_models.SubmissionGroup.objects.count())

        subtest = create_group()
        self.client.force_authenticate(self.admin)
        response = self.client.patch(self.group_url(group),
                                     {'member_names': new_member_names})
        subtest.join()
        self.assertEqual(status.HTTP_400_BAD_REQUEST, response.status_code)
        group.refresh_from_db()
        self.assertNotIn(overlap_member.username, group.member_names)

    def test_update_group_and_create_invitation_with_invitor_in_both(self):
        self.fail()

    def test_update_group_and_create_invitation_with_member_in_both(self):
        self.fail()

    def test_two_final_invitation_acceptances_race_condition_prevented(self):
        self.fail()

    def test_final_invitation_accept_and_create(self):
        self.fail()
