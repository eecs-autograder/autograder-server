from django.test import tag
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APIClient

import autograder.core.models as ag_models
import autograder.utils.testing as test_ut
import autograder.utils.testing.model_obj_builders as obj_build


@tag('slow')
class RaceConditionTestCase(test_ut.TransactionUnitTestBase):
    def setUp(self):
        super().setUp()
        self.client = APIClient()
        self.project = obj_build.make_project(
            max_group_size=4, visible_to_students=True, guests_can_submit=True)
        self.admin = obj_build.make_admin_user(self.project.course)

    def test_create_group_and_invitation_with_sender_in_both(self):
        sender = obj_build.make_user()
        path = 'autograder.rest_api.views.group_views.test_ut.mocking_hook'

        @test_ut.sleeper_subtest(path)
        def create_group(project_id):
            project = ag_models.Project.objects.get(pk=project_id)
            client = APIClient()
            client.force_authenticate(self.admin)
            response = client.post(
                reverse('groups', kwargs={'project_pk': project.pk}),
                {'member_names': [sender.username, 'this_one']})
            self.assertEqual(status.HTTP_201_CREATED, response.status_code)
            self.assertEqual(1, ag_models.Group.objects.count())

        subtest = create_group(self.project.id)
        self.client.force_authenticate(sender)
        response = self.client.post(
            reverse('group-invitations', kwargs={'pk': self.project.pk}),
            {'invited_usernames': ['other_one']})
        subtest.join()
        self.assertEqual(1, ag_models.Group.objects.count())
        self.assertEqual(status.HTTP_400_BAD_REQUEST, response.status_code)

    def test_create_group_and_invitation_with_member_in_both(self):
        sender = obj_build.create_dummy_user()
        overlap_username = 'steve'
        path = 'autograder.rest_api.views.group_views.test_ut.mocking_hook'

        @test_ut.sleeper_subtest(path)
        def do_request_and_wait(project_id):
            project = ag_models.Project.objects.get(pk=project_id)
            client = APIClient()
            client.force_authenticate(self.admin)
            response = client.post(
                reverse('groups', kwargs={'project_pk': project.pk}),
                {'member_names': [overlap_username, 'this_one']})
            self.assertEqual(status.HTTP_201_CREATED, response.status_code)
            self.assertEqual(1, ag_models.Group.objects.count())

        subtest = do_request_and_wait(self.project.pk)
        self.client.force_authenticate(sender)
        response = self.client.post(
            reverse('group-invitations', kwargs={'pk': self.project.pk}),
            {'invited_usernames': [overlap_username]})
        subtest.join()
        self.assertEqual(status.HTTP_400_BAD_REQUEST, response.status_code)
        self.assertEqual(1, ag_models.Group.objects.count())

    def test_create_groups_with_member_overlap(self):
        overlap_username = 'stave'
        path = 'autograder.rest_api.views.group_views.test_ut.mocking_hook'

        @test_ut.sleeper_subtest(path)
        def do_request_and_wait(project_id):
            project = ag_models.Project.objects.get(pk=project_id)
            client = APIClient()
            client.force_authenticate(self.admin)
            response = client.post(
                reverse('groups', kwargs={'project_pk': project.pk}),
                {'member_names': [overlap_username, 'this_one']})
            self.assertEqual(status.HTTP_201_CREATED, response.status_code)
            self.assertEqual(1, ag_models.Group.objects.count())

        subtest = do_request_and_wait(self.project.pk)
        self.client.force_authenticate(self.admin)
        response = self.client.post(
            reverse('groups', kwargs={'project_pk': self.project.pk}),
            {'member_names': [overlap_username, 'other_one']})
        subtest.join()
        self.assertEqual(status.HTTP_400_BAD_REQUEST, response.status_code)
        self.assertEqual(1, ag_models.Group.objects.count())

    def test_update_groups_with_member_overlap(self):
        first_group = obj_build.make_group(
            project=self.project, members_role=obj_build.UserRole.admin)
        second_group = obj_build.make_group(
            project=self.project, members_role=obj_build.UserRole.staff)
        overlap_member = obj_build.make_staff_user(self.project.course)
        path = 'autograder.rest_api.views.group_views.test_ut.mocking_hook'

        @test_ut.sleeper_subtest(path)
        def update_first_group():
            client = APIClient()
            client.force_authenticate(self.admin)
            member_names = [overlap_member.username] + first_group.member_names
            response = client.patch(reverse('group-detail', kwargs={'pk': first_group.pk}),
                                    {'member_names': member_names})
            self.assertEqual(status.HTTP_200_OK, response.status_code)
            first_group.refresh_from_db()
            self.assertCountEqual(member_names, first_group.member_names)

        subtest = update_first_group()
        self.client.force_authenticate(self.admin)
        member_names = ([overlap_member.username] + second_group.member_names)
        response = self.client.patch(reverse('group-detail', kwargs={'pk': second_group.pk}),
                                     {'member_names': member_names})
        subtest.join()
        self.assertEqual(status.HTTP_400_BAD_REQUEST, response.status_code)
        second_group.refresh_from_db()
        self.assertNotIn(overlap_member.username, second_group.member_names)

    def test_create_and_update_groups_with_member_overlap(self):
        group = obj_build.make_group(
            project=self.project, members_role=obj_build.UserRole.admin)
        overlap_member = obj_build.make_staff_user(self.project.course)
        new_member_names = group.member_names + [overlap_member.username]
        path = 'autograder.rest_api.views.group_views.test_ut.mocking_hook'
        self.assertEqual(1, ag_models.Group.objects.count())

        @test_ut.sleeper_subtest(path)
        def create_group():
            client = APIClient()
            client.force_authenticate(self.admin)
            member_names = [
                overlap_member.username,
                obj_build.make_staff_user(self.project.course).username
            ]
            response = client.post(reverse('groups', kwargs={'project_pk': self.project.pk}),
                                   {'member_names': member_names})
            self.assertEqual(status.HTTP_201_CREATED, response.status_code, msg=response.data)
            self.assertEqual(2, ag_models.Group.objects.count())

        subtest = create_group()
        self.client.force_authenticate(self.admin)
        response = self.client.patch(reverse('group-detail', kwargs={'pk': group.pk}),
                                     {'member_names': new_member_names})
        subtest.join()
        self.assertEqual(status.HTTP_400_BAD_REQUEST, response.status_code)
        group.refresh_from_db()
        self.assertNotIn(overlap_member.username, group.member_names)

    def test_update_group_and_create_invitation_with_sender_in_both(self):
        group = obj_build.make_group(
            project=self.project, members_role=obj_build.UserRole.admin)
        sender = obj_build.make_admin_user(self.project.course)
        path = 'autograder.rest_api.views.group_views.test_ut.mocking_hook'

        @test_ut.sleeper_subtest(path)
        def update_group():
            client = APIClient()
            client.force_authenticate(self.admin)
            response = client.patch(
                reverse('group-detail', kwargs={'pk': group.pk}),
                {'member_names': [sender.username] + group.member_names})
            self.assertEqual(status.HTTP_200_OK, response.status_code)
            self.assertIn(sender.username, response.data['member_names'])

        subtest = update_group()
        self.client.force_authenticate(sender)
        response = self.client.post(
            reverse('group-invitations', kwargs={'pk': self.project.pk}),
            {'invited_usernames': [obj_build.make_admin_user(self.project.course).username]})
        subtest.join()
        self.assertEqual(status.HTTP_400_BAD_REQUEST, response.status_code)
        self.assertEqual(0, ag_models.GroupInvitation.objects.count())

    def test_update_group_and_create_invitation_with_member_in_both(self):
        group = obj_build.make_group(
            project=self.project, members_role=obj_build.UserRole.admin)
        new_member = obj_build.make_admin_user(self.project.course)
        path = 'autograder.rest_api.views.group_views.test_ut.mocking_hook'

        @test_ut.sleeper_subtest(path)
        def update_group():
            client = APIClient()
            client.force_authenticate(self.admin)
            response = client.patch(
                reverse('group-detail', kwargs={'pk': group.pk}),
                {'member_names': [new_member.username] + group.member_names})
            self.assertEqual(status.HTTP_200_OK, response.status_code)
            self.assertIn(new_member.username, response.data['member_names'])

        subtest = update_group()
        sender = obj_build.make_admin_user(self.project.course)
        self.client.force_authenticate(sender)
        response = self.client.post(
            reverse('group-invitations', kwargs={'pk': self.project.pk}),
            {'invited_usernames': [new_member.username]})
        subtest.join()
        self.assertEqual(status.HTTP_400_BAD_REQUEST, response.status_code)
        self.assertEqual(0, ag_models.GroupInvitation.objects.count())

    def test_two_different_final_invitation_acceptances_sender_overlap(self):
        first_recipient = obj_build.make_admin_user(self.project.course)
        sender_and_second_recipient = obj_build.make_admin_user(self.project.course)
        second_sender = obj_build.make_admin_user(self.project.course)

        first_invitation = (
            ag_models.GroupInvitation.objects.validate_and_create(
                sender_and_second_recipient, [first_recipient], project=self.project))
        second_invitation = (
            ag_models.GroupInvitation.objects.validate_and_create(
                second_sender, [sender_and_second_recipient], project=self.project))

        path = 'autograder.rest_api.views.group_invitation_views.test_ut.mocking_hook'

        @test_ut.sleeper_subtest(path)
        def first_final_accept():
            client = APIClient()
            client.force_authenticate(first_recipient)
            response = client.post(self.accept_invitation_url(first_invitation))
            self.assertEqual(status.HTTP_201_CREATED, response.status_code)
            self.assertEqual(1, ag_models.Group.objects.count())

        subtest = first_final_accept()
        self.client.force_authenticate(sender_and_second_recipient)
        response = self.client.post(self.accept_invitation_url(second_invitation))
        subtest.join()
        self.assertEqual(status.HTTP_400_BAD_REQUEST, response.status_code)
        self.assertEqual(1, ag_models.Group.objects.count())

    def test_two_different_final_invitation_acceptances_member_overlap(self):
        first_sender = obj_build.make_admin_user(self.project.course)
        second_sender = obj_build.make_admin_user(self.project.course)
        recipient = obj_build.make_admin_user(self.project.course)

        first_invitation = (
            ag_models.GroupInvitation.objects.validate_and_create(
                first_sender, [recipient], project=self.project))
        second_invitation = (
            ag_models.GroupInvitation.objects.validate_and_create(
                second_sender, [recipient], project=self.project))

        path = 'autograder.rest_api.views.group_invitation_views.test_ut.mocking_hook'

        @test_ut.sleeper_subtest(path)
        def first_final_accept():
            client = APIClient()
            client.force_authenticate(recipient)
            response = client.post(self.accept_invitation_url(first_invitation))
            self.assertEqual(status.HTTP_201_CREATED, response.status_code)
            self.assertEqual(1, ag_models.Group.objects.count())

        subtest = first_final_accept()
        self.client.force_authenticate(recipient)
        response = self.client.post(self.accept_invitation_url(second_invitation))
        subtest.join()
        self.assertEqual(status.HTTP_400_BAD_REQUEST, response.status_code)
        self.assertEqual(1, ag_models.Group.objects.count())

    def test_create_group_and_final_invitation_accept_sender_overlap(self):
        sender = obj_build.make_admin_user(self.project.course)
        other_member = obj_build.make_admin_user(self.project.course)

        invitation = (
            ag_models.GroupInvitation.objects.validate_and_create(
                sender, [other_member], project=self.project))

        path = 'autograder.rest_api.views.group_views.test_ut.mocking_hook'

        @test_ut.sleeper_subtest(path)
        def create_group():
            client = APIClient()
            client.force_authenticate(self.admin)
            response = client.post(
                reverse('groups', kwargs={'project_pk': self.project.pk}),
                {'member_names': [sender.username]})
            self.assertEqual(status.HTTP_201_CREATED, response.status_code)
            self.assertEqual(1, ag_models.Group.objects.count())

        subtest = create_group()
        self.client.force_authenticate(other_member)
        response = self.client.post(self.accept_invitation_url(invitation))
        subtest.join()
        self.assertEqual(status.HTTP_400_BAD_REQUEST, response.status_code)
        self.assertEqual(1, ag_models.Group.objects.count())

    def test_create_group_and_final_invitation_accept_member_overlap(self):
        sender = obj_build.make_admin_user(self.project.course)
        other_member = obj_build.make_admin_user(self.project.course)

        invitation = (
            ag_models.GroupInvitation.objects.validate_and_create(
                sender, [other_member], project=self.project))

        path = 'autograder.rest_api.views.group_views.test_ut.mocking_hook'

        @test_ut.sleeper_subtest(path)
        def create_group():
            client = APIClient()
            client.force_authenticate(self.admin)
            response = client.post(
                reverse('groups', kwargs={'project_pk': self.project.pk}),
                {'member_names': [other_member.username]})
            self.assertEqual(status.HTTP_201_CREATED, response.status_code)
            self.assertEqual(1, ag_models.Group.objects.count())

        subtest = create_group()
        self.client.force_authenticate(other_member)
        response = self.client.post(self.accept_invitation_url(invitation))
        subtest.join()
        self.assertEqual(status.HTTP_400_BAD_REQUEST, response.status_code)
        self.assertEqual(1, ag_models.Group.objects.count())

    def test_update_group_and_final_invitation_accept_sender_overlap(self):
        sender = obj_build.make_admin_user(self.project.course)
        other_member = obj_build.make_admin_user(self.project.course)

        invitation = (
            ag_models.GroupInvitation.objects.validate_and_create(
                sender, [other_member], project=self.project))
        group = obj_build.make_group(
            project=self.project, members_role=obj_build.UserRole.admin)

        path = 'autograder.rest_api.views.group_views.test_ut.mocking_hook'

        @test_ut.sleeper_subtest(path)
        def update_group():
            client = APIClient()
            client.force_authenticate(self.admin)
            response = client.patch(
                reverse('group-detail', kwargs={'pk': group.pk}),
                {'member_names': [sender.username] + group.member_names})
            self.assertEqual(status.HTTP_200_OK, response.status_code)
            self.assertIn(sender.username, response.data['member_names'])

        subtest = update_group()
        self.client.force_authenticate(other_member)
        response = self.client.post(self.accept_invitation_url(invitation))
        subtest.join()
        self.assertEqual(status.HTTP_400_BAD_REQUEST, response.status_code)
        self.assertEqual(1, ag_models.Group.objects.count())

    def test_update_group_and_final_invitation_accept_member_overlap(self):
        sender = obj_build.make_admin_user(self.project.course)
        other_member = obj_build.make_admin_user(self.project.course)

        invitation = (
            ag_models.GroupInvitation.objects.validate_and_create(
                sender, [other_member], project=self.project))
        group = obj_build.make_group(project=self.project, members_role=obj_build.UserRole.admin)

        path = 'autograder.rest_api.views.group_views.test_ut.mocking_hook'

        @test_ut.sleeper_subtest(path)
        def update_group():
            client = APIClient()
            client.force_authenticate(self.admin)
            response = client.patch(
                reverse('group-detail', kwargs={'pk': group.pk}),
                {'member_names': [other_member.username] + group.member_names})
            self.assertEqual(status.HTTP_200_OK, response.status_code)
            self.assertIn(other_member.username, response.data['member_names'])

        subtest = update_group()
        self.client.force_authenticate(other_member)
        response = self.client.post(self.accept_invitation_url(invitation))
        subtest.join()
        self.assertEqual(status.HTTP_400_BAD_REQUEST, response.status_code)
        self.assertEqual(1, ag_models.Group.objects.count())

    def accept_invitation_url(self, invitation: ag_models.GroupInvitation):
        return reverse('accept-group-invitation', kwargs={'pk': invitation.pk})
