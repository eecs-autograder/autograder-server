from django.test import tag
from rest_framework import status
from rest_framework.test import APIClient

import autograder.core.models as ag_models
import autograder.rest_api.tests.test_views.common_generic_data as test_data
import autograder.utils.testing as test_ut
import autograder.utils.testing.model_obj_builders as obj_build
from autograder.rest_api.views.group_views.group_detail_view import GroupDetailViewSet
from autograder.rest_api.views.group_views.groups_view import (
    GroupsViewSet)


@tag('slow')
class RaceConditionTestCase(test_data.Client,
                            test_data.Project,
                            test_data.Group,
                            test_ut.UnitTestBase):
    def test_create_group_and_invitation_with_invitor_in_both(self):
        self.visible_public_project.validate_and_update(max_group_size=4)
        project_id = self.visible_public_project.pk
        invitor = obj_build.create_dummy_user()
        path = 'autograder.rest_api.views.group_views.groups_view.GroupsViewSet.serializer_class'

        @test_ut.sleeper_subtest(path, wraps=GroupsViewSet.serializer_class)
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
        invitor = obj_build.create_dummy_user()
        overlap_username = 'steve'
        path = 'autograder.rest_api.views.group_views.groups_view.GroupsViewSet.serializer_class'

        @test_ut.sleeper_subtest(path, wraps=GroupsViewSet.serializer_class)
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
        path = 'autograder.rest_api.views.group_views.groups_view.GroupsViewSet.serializer_class'

        @test_ut.sleeper_subtest(path, wraps=GroupsViewSet.serializer_class)
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
                '.group_detail_view.GroupDetailViewSet.serializer_class')

        @test_ut.sleeper_subtest(path, wraps=GroupDetailViewSet.serializer_class)
        def update_first_group():
            client = APIClient()
            client.force_authenticate(self.admin)
            member_names = [overlap_member.username] + first_group.member_names
            response = client.patch(self.group_url(first_group),
                                    {'member_names': member_names})
            self.assertEqual(status.HTTP_200_OK, response.status_code)
            first_group.refresh_from_db()
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

    def test_create_and_update_groups_with_member_overlap(self):
        self.project.validate_and_update(max_group_size=4)
        group = self.admin_group(self.project)
        overlap_member = self.clone_user(self.staff)
        new_member_names = group.member_names + [overlap_member.username]
        path = 'autograder.rest_api.views.group_views.groups_view.GroupsViewSet.serializer_class'
        self.assertEqual(1, ag_models.SubmissionGroup.objects.count())

        @test_ut.sleeper_subtest(path, wraps=GroupsViewSet.serializer_class)
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
        self.project.validate_and_update(max_group_size=4)
        group = self.admin_group(self.project)
        invitor = self.clone_user(self.admin)
        path = ('autograder.rest_api.views.group_views'
                '.group_detail_view.GroupDetailViewSet.serializer_class')

        @test_ut.sleeper_subtest(path, wraps=GroupDetailViewSet.serializer_class)
        def update_group():
            client = APIClient()
            client.force_authenticate(self.admin)
            response = client.patch(
                self.group_url(group),
                {'member_names': [invitor.username] + group.member_names})
            self.assertEqual(status.HTTP_200_OK, response.status_code)
            self.assertIn(invitor.username, response.data['member_names'])

        subtest = update_group()
        self.client.force_authenticate(invitor)
        response = self.client.post(
            self.get_invitations_url(self.project),
            {'invited_usernames': [self.clone_user(self.admin).username]})
        subtest.join()
        self.assertEqual(status.HTTP_400_BAD_REQUEST, response.status_code)
        self.assertEqual(0, ag_models.SubmissionGroupInvitation.objects.count())

    def test_update_group_and_create_invitation_with_member_in_both(self):
        self.project.validate_and_update(max_group_size=4)
        group = self.admin_group(self.project)
        new_member = self.clone_user(self.admin)
        path = ('autograder.rest_api.views.group_views'
                '.group_detail_view.GroupDetailViewSet.serializer_class')

        @test_ut.sleeper_subtest(path, wraps=GroupDetailViewSet.serializer_class)
        def update_group():
            client = APIClient()
            client.force_authenticate(self.admin)
            response = client.patch(
                self.group_url(group),
                {'member_names': [new_member.username] + group.member_names})
            self.assertEqual(status.HTTP_200_OK, response.status_code)
            self.assertIn(new_member.username, response.data['member_names'])

        subtest = update_group()
        invitor = self.clone_user(self.admin)
        self.client.force_authenticate(invitor)
        response = self.client.post(
            self.get_invitations_url(self.project),
            {'invited_usernames': [new_member.username]})
        subtest.join()
        self.assertEqual(status.HTTP_400_BAD_REQUEST, response.status_code)
        self.assertEqual(0, ag_models.SubmissionGroupInvitation.objects.count())

    def test_two_different_final_invitation_acceptances_invitor_overlap(self):
        self.project.validate_and_update(max_group_size=2)
        first_invitee = self.clone_user(self.admin)
        invitor_and_second_invitee = self.clone_user(self.admin)
        second_invitor = self.clone_user(self.admin)

        first_invitation = (
            ag_models.SubmissionGroupInvitation.objects.validate_and_create(
                invitor_and_second_invitee, [first_invitee], project=self.project))
        second_invitation = (
            ag_models.SubmissionGroupInvitation.objects.validate_and_create(
                second_invitor, [invitor_and_second_invitee], project=self.project))

        path = ('autograder.rest_api.views.group_invitation_views.'
                'group_invitation_detail_view.test_ut.mocking_hook')

        @test_ut.sleeper_subtest(path)
        def first_final_accept():
            client = APIClient()
            client.force_authenticate(first_invitee)
            response = client.post(self.invitation_url(first_invitation))
            self.assertEqual(status.HTTP_201_CREATED, response.status_code)
            self.assertEqual(1, ag_models.SubmissionGroup.objects.count())

        subtest = first_final_accept()
        self.client.force_authenticate(invitor_and_second_invitee)
        response = self.client.post(self.invitation_url(second_invitation))
        subtest.join()
        self.assertEqual(status.HTTP_400_BAD_REQUEST, response.status_code)
        self.assertEqual(1, ag_models.SubmissionGroup.objects.count())

    def test_two_different_final_invitation_acceptances_member_overlap(self):
        self.project.validate_and_update(max_group_size=2)
        first_invitor = self.clone_user(self.admin)
        second_invitor = self.clone_user(self.admin)
        invitee = self.clone_user(self.admin)

        first_invitation = (
            ag_models.SubmissionGroupInvitation.objects.validate_and_create(
                first_invitor, [invitee], project=self.project))
        second_invitation = (
            ag_models.SubmissionGroupInvitation.objects.validate_and_create(
                second_invitor, [invitee], project=self.project))

        path = ('autograder.rest_api.views'
                '.group_invitation_views.group_invitation_detail_view.test_ut.mocking_hook')

        @test_ut.sleeper_subtest(path)
        def first_final_accept():
            client = APIClient()
            client.force_authenticate(invitee)
            response = client.post(self.invitation_url(first_invitation))
            self.assertEqual(status.HTTP_201_CREATED, response.status_code)
            self.assertEqual(1, ag_models.SubmissionGroup.objects.count())

        subtest = first_final_accept()
        self.client.force_authenticate(invitee)
        response = self.client.post(self.invitation_url(second_invitation))
        subtest.join()
        self.assertEqual(status.HTTP_400_BAD_REQUEST, response.status_code)
        self.assertEqual(1, ag_models.SubmissionGroup.objects.count())

    def test_create_group_and_final_invitation_accept_invitor_overlap(self):
        self.project.validate_and_update(max_group_size=2)
        invitor = self.clone_user(self.admin)
        other_member = self.clone_user(self.admin)

        invitation = (
            ag_models.SubmissionGroupInvitation.objects.validate_and_create(
                invitor, [other_member], project=self.project))

        path = 'autograder.rest_api.views.group_views.groups_view.test_ut.mocking_hook'

        @test_ut.sleeper_subtest(path)
        def create_group():
            client = APIClient()
            client.force_authenticate(self.admin)
            response = client.post(
                self.get_groups_url(self.project),
                {'member_names': [invitor.username]})
            self.assertEqual(status.HTTP_201_CREATED, response.status_code)
            self.assertEqual(1, ag_models.SubmissionGroup.objects.count())

        subtest = create_group()
        self.client.force_authenticate(other_member)
        response = self.client.post(self.invitation_url(invitation))
        subtest.join()
        self.assertEqual(status.HTTP_400_BAD_REQUEST, response.status_code)
        self.assertEqual(1, ag_models.SubmissionGroup.objects.count())

    def test_create_group_and_final_invitation_accept_member_overlap(self):
        self.project.validate_and_update(max_group_size=2)
        invitor = self.clone_user(self.admin)
        other_member = self.clone_user(self.admin)

        invitation = (
            ag_models.SubmissionGroupInvitation.objects.validate_and_create(
                invitor, [other_member], project=self.project))

        path = 'autograder.rest_api.views.group_views.groups_view.test_ut.mocking_hook'

        @test_ut.sleeper_subtest(path)
        def create_group():
            client = APIClient()
            client.force_authenticate(self.admin)
            response = client.post(
                self.get_groups_url(self.project),
                {'member_names': [other_member.username]})
            self.assertEqual(status.HTTP_201_CREATED, response.status_code)
            self.assertEqual(1, ag_models.SubmissionGroup.objects.count())

        subtest = create_group()
        self.client.force_authenticate(other_member)
        response = self.client.post(self.invitation_url(invitation))
        subtest.join()
        self.assertEqual(status.HTTP_400_BAD_REQUEST, response.status_code)
        self.assertEqual(1, ag_models.SubmissionGroup.objects.count())

    def test_update_group_and_final_invitation_accept_invitor_overlap(self):
        self.project.validate_and_update(max_group_size=4)
        invitor = self.clone_user(self.admin)
        other_member = self.clone_user(self.admin)

        invitation = (
            ag_models.SubmissionGroupInvitation.objects.validate_and_create(
                invitor, [other_member], project=self.project))
        group = self.admin_group(self.project)

        path = ('autograder.rest_api.views.group_views'
                '.group_detail_view.test_ut.mocking_hook')

        @test_ut.sleeper_subtest(path)
        def update_group():
            client = APIClient()
            client.force_authenticate(self.admin)
            response = client.patch(
                self.group_url(group),
                {'member_names': [invitor.username] + group.member_names})
            self.assertEqual(status.HTTP_200_OK, response.status_code)
            self.assertIn(invitor.username, response.data['member_names'])

        subtest = update_group()
        self.client.force_authenticate(other_member)
        response = self.client.post(self.invitation_url(invitation))
        subtest.join()
        self.assertEqual(status.HTTP_400_BAD_REQUEST, response.status_code)
        self.assertEqual(1, ag_models.SubmissionGroup.objects.count())

    def test_update_group_and_final_invitation_accept_member_overlap(self):
        self.project.validate_and_update(max_group_size=4)
        invitor = self.clone_user(self.admin)
        other_member = self.clone_user(self.admin)

        invitation = (
            ag_models.SubmissionGroupInvitation.objects.validate_and_create(
                invitor, [other_member], project=self.project))
        group = self.admin_group(self.project)

        path = ('autograder.rest_api.views.group_views'
                '.group_detail_view.test_ut.mocking_hook')

        @test_ut.sleeper_subtest(path)
        def update_group():
            client = APIClient()
            client.force_authenticate(self.admin)
            response = client.patch(
                self.group_url(group),
                {'member_names': [other_member.username] + group.member_names})
            self.assertEqual(status.HTTP_200_OK, response.status_code)
            self.assertIn(other_member.username, response.data['member_names'])

        subtest = update_group()
        self.client.force_authenticate(other_member)
        response = self.client.post(self.invitation_url(invitation))
        subtest.join()
        self.assertEqual(status.HTTP_400_BAD_REQUEST, response.status_code)
        self.assertEqual(1, ag_models.SubmissionGroup.objects.count())
