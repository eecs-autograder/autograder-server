import itertools

from django.core.urlresolvers import reverse
from django.core.exceptions import ObjectDoesNotExist

from autograder.core.models import (
    SubmissionGroupInvitation, SubmissionGroup)
from autograder.core.tests.temporary_filesystem_test_case import (
    TemporaryFilesystemTestCase)
import autograder.core.tests.dummy_object_utils as obj_ut
from .utilities import MockClient, json_load_bytes, sorted_by_pk
from autograder.rest_api import url_shortcuts


class GetAcceptRejectSubmissionGroupInvitationTestCase(TemporaryFilesystemTestCase):
    def setUp(self):
        super().setUp()

        self.invitations = {
            key: {
                'invitor': obj_ut.create_dummy_user(),
                'invitees': obj_ut.create_dummy_users(2),
            }
            for key in ('admin', 'staff', 'enrolled', 'nobody')
        }

        self.admins = (
            [self.invitations['admin']['invitor']] +
            self.invitations['admin']['invitees'])
        self.staff = (
            [self.invitations['staff']['invitor']] +
            self.invitations['staff']['invitees'])
        self.enrolled = (
            [self.invitations['enrolled']['invitor']] +
            self.invitations['enrolled']['invitees'])

        self.project = obj_ut.build_project(
            course_kwargs={'administrators': self.admins},
            semester_kwargs={'staff': self.staff,
                             'enrolled_students': self.enrolled},
            project_kwargs={
                'allow_submissions_from_non_enrolled_students': True,
                'visible_to_students': True,
                'max_group_size': 3})

        self.semester = self.project.semester
        self.course = self.semester.course

        self.project_url = reverse(
            'project:get', kwargs={'pk': self.project.pk})

        for key, value in self.invitations.items():
            value['invitation'] = (
                SubmissionGroupInvitation.objects.validate_and_create(
                    invited_users=[
                        user.username for user in value['invitees']],
                    invitation_creator=value['invitor'].username,
                    project=self.project))
            value['url'] = reverse('invitation:get',
                                   kwargs={'pk': value['invitation'].pk})
            value['accept_url'] = reverse(
                'invitation:accept', kwargs={'pk': value['invitation'].pk})

    def test_invitation_creator_view_invitation(self):
        for key, value in self.invitations.items():
            acceptor = value['invitees'][0]
            value['invitation'].invitee_accept(acceptor.username)

            client = MockClient(value['invitor'])
            response = client.get(value['url'])
            self.assertEqual(200, response.status_code)

            expected_content = {
                "type": "submission_group_invitation",
                "id": value['invitation'].pk,
                "invitation_creator": value['invitor'].username,
                "invited_members_to_acceptance": {
                    user.username: user == acceptor
                    for user in value['invitees']
                },
                "semester_name": self.semester.name,
                "project_name": self.project.name,
                "urls": {
                    "self": value['url'],
                    "accept": value['accept_url'],
                    "project": self.project_url
                }
            }

            self.assertEqual(
                expected_content, json_load_bytes(response.content))

    def test_invitee_view_invitation(self):
        for key, value in self.invitations.items():
            acceptor = value['invitees'][0]
            value['invitation'].invitee_accept(acceptor.username)

            client = MockClient(value['invitees'][0])
            response = client.get(value['url'])
            self.assertEqual(200, response.status_code)

            expected_content = {
                "type": "submission_group_invitation",
                "id": value['invitation'].pk,
                "invitation_creator": value['invitor'].username,
                "invited_members_to_acceptance": {
                    user.username: user == acceptor
                    for user in value['invitees']
                },
                "semester_name": self.semester.name,
                "project_name": self.project.name,
                "urls": {
                    "self": value['url'],
                    "accept": value['accept_url'],
                    "project": self.project_url
                }
            }

            self.assertEqual(
                expected_content, json_load_bytes(response.content))

    def test_other_view_invitation_permission_denied(self):
        for viewer, to_view in itertools.product(self.invitations.values(),
                                                 self.invitations.values()):
            if viewer is to_view:
                continue

            self._do_get_invitation_permission_denied_test(
                viewer['invitor'], to_view['url'])
            self._do_get_invitation_permission_denied_test(
                viewer['invitees'][0], to_view['url'])

    def test_student_view_invitation_project_hidden_permission_denied(self):
        self.project.visible_to_students = False
        self.project.validate_and_save()
        for obj in self.invitations['enrolled'], self.invitations['nobody']:
            self._do_get_invitation_permission_denied_test(
                obj['invitor'], obj['url'])
            self._do_get_invitation_permission_denied_test(
                obj['invitees'][0], obj['url'])

    def test_non_enrolled_student_non_public_project_view_invitation_permission_denied(self):
        self.project.allow_submissions_from_non_enrolled_students = False
        self.project.validate_and_save()

        obj = self.invitations['nobody']
        self._do_get_invitation_permission_denied_test(
            obj['invitor'], obj['url'])
        self._do_get_invitation_permission_denied_test(
            obj['invitees'][0], obj['url'])

    def _do_get_invitation_permission_denied_test(self, user, to_view_url):
        client = MockClient(user)
        response = client.get(to_view_url)
        self.assertEqual(403, response.status_code)

    # -------------------------------------------------------------------------

    def test_all_invitees_accept_invitation(self):
        # make sure other invitations involving those users are deleted
        # make sure notifications are sent
        # make sure invitation is deleted once everyone accepts

        for obj in self.invitations.values():
            invitor = obj['invitor']
            invitees = obj['invitees']
            other_invitation = (
                SubmissionGroupInvitation.objects.validate_and_create(
                    invitation_creator=invitor.username,
                    invited_users=[user.username for user in invitees],
                    project=self.project))
            for user in invitees:
                client = MockClient(user)
                response = client.post(obj['accept_url'], {})
                if user == invitees[-1]:
                    self.assertEqual(201, response.status_code)
                    group = SubmissionGroup.get_group(
                        invitees[0], self.project)
                    self.assertEqual(
                        response.content.decode('utf-8'),
                        url_shortcuts.group_url(group))
                else:
                    self.assertEqual(204, response.status_code)

            with self.assertRaises(ObjectDoesNotExist):
                SubmissionGroupInvitation.objects.get(pk=obj['invitation'].pk)

            with self.assertRaises(ObjectDoesNotExist):
                SubmissionGroupInvitation.objects.get(pk=other_invitation.pk)

            for user in invitees:
                self.assertEqual(1, user.notifications.count())

            self.assertEqual(2, invitor.notifications.count())

            self.assertCountEqual(
                group.members.all(), itertools.chain([invitor], invitees))

    def test_invitee_reject_invitation(self):
        # make sure notifications are sent and invitation is deleted
        # make sure other invitations are NOT deleted
        for obj in self.invitations.values():
            invitor = obj['invitor']
            invitees = obj['invitees']
            other_invitation = (
                SubmissionGroupInvitation.objects.validate_and_create(
                    invitation_creator=invitor.username,
                    invited_users=[user.username for user in invitees],
                    project=self.project))
            rejector = invitees[0]
            client = MockClient(rejector)
            response = client.delete(obj['url'])
            self.assertEqual(204, response.status_code)

            for user in invitor, invitees[1]:
                self.assertEqual(1, user.notifications.count())

            with self.assertRaises(ObjectDoesNotExist):
                SubmissionGroupInvitation.objects.get(pk=obj['invitation'].pk)

            SubmissionGroupInvitation.objects.get(pk=other_invitation.pk)

    def test_some_invitees_accept_one_rejects(self):
        # make sure notifications are sent and invitation is deleted
        # make sure other invitations are NOT deleted
        for obj in self.invitations.values():
            invitor = obj['invitor']
            invitees = obj['invitees']
            other_invitation = (
                SubmissionGroupInvitation.objects.validate_and_create(
                    invitation_creator=invitor.username,
                    invited_users=[user.username for user in invitees],
                    project=self.project))
            acceptor = invitees[0]
            client = MockClient(acceptor)
            response = client.post(obj['accept_url'], {})
            for user in invitees[1], invitor:
                self.assertEqual(1, user.notifications.count())

            rejector = invitees[1]
            client = MockClient(rejector)
            response = client.delete(obj['url'])
            self.assertEqual(204, response.status_code)

            self.assertEqual(2, invitor.notifications.count())
            for user in acceptor, rejector:
                self.assertEqual(1, user.notifications.count())

            with self.assertRaises(ObjectDoesNotExist):
                SubmissionGroupInvitation.objects.get(pk=obj['invitation'].pk)

            with self.assertRaises(ObjectDoesNotExist):
                SubmissionGroup.get_group(invitor, self.project)

            SubmissionGroupInvitation.objects.get(pk=other_invitation.pk)

    def test_invitation_creator_revokes_invitation(self):
        # make sure notifications are sent and invitation is deleted
        # make sure other invitations are NOT deleted
        for obj in self.invitations.values():
            invitor = obj['invitor']
            invitees = obj['invitees']
            other_invitation = (
                SubmissionGroupInvitation.objects.validate_and_create(
                    invitation_creator=invitor.username,
                    invited_users=[user.username for user in invitees],
                    project=self.project))

            client = MockClient(invitor)
            response = client.delete(obj['url'])
            self.assertEqual(204, response.status_code)

            for user in invitees:
                self.assertEqual(1, user.notifications.count())

            with self.assertRaises(ObjectDoesNotExist):
                SubmissionGroupInvitation.objects.get(pk=obj['invitation'].pk)

            with self.assertRaises(ObjectDoesNotExist):
                SubmissionGroup.get_group(invitor, self.project)

            SubmissionGroupInvitation.objects.get(pk=other_invitation.pk)

    # -------------------------------------------------------------------------

    def test_student_accept_invitation_project_hidden_permission_denied(self):
        self.project.visible_to_students = False
        self.project.validate_and_save()
        for obj in self.invitations['enrolled'], self.invitations['nobody']:
            self._do_accept_permission_denied_test(
                obj['invitor'], obj['invitation'], obj['accept_url'])
            self._do_accept_permission_denied_test(
                obj['invitees'][0], obj['invitation'], obj['accept_url'])

    def test_student_reject_invitation_project_hidden_permission_denied(self):
        self.project.visible_to_students = False
        self.project.validate_and_save()
        for obj in self.invitations['enrolled'], self.invitations['nobody']:
            self._do_reject_permission_denied_test(
                obj['invitor'], obj['invitation'], obj['url'])
            self._do_reject_permission_denied_test(
                obj['invitees'][0], obj['invitation'], obj['url'])

    def test_non_enrolled_student_accept_non_public_project_permission_denied(self):
        self.project.allow_submissions_from_non_enrolled_students = False
        self.project.validate_and_save()
        obj = self.invitations['nobody']
        self._do_accept_permission_denied_test(
            obj['invitor'], obj['invitation'], obj['accept_url'])
        self._do_accept_permission_denied_test(
            obj['invitees'][0], obj['invitation'], obj['accept_url'])

    def test_non_enrolled_student_reject_non_public_project_permission_denied(self):
        self.project.allow_submissions_from_non_enrolled_students = False
        self.project.validate_and_save()
        obj = self.invitations['nobody']
        self._do_reject_permission_denied_test(
            obj['invitor'], obj['invitation'], obj['url'])
        self._do_reject_permission_denied_test(
            obj['invitees'][0], obj['invitation'], obj['url'])

    def test_non_involved_user_accept_permission_denied(self):
        for acceptor_obj, to_accept_obj in itertools.product(
                self.invitations.values(), self.invitations.values()):
            if acceptor_obj is to_accept_obj:
                continue

            self._do_accept_permission_denied_test(
                acceptor_obj['invitor'], to_accept_obj['invitation'],
                to_accept_obj['accept_url'])
            self._do_accept_permission_denied_test(
                acceptor_obj['invitees'][0], to_accept_obj['invitation'],
                to_accept_obj['accept_url'])

    def test_non_involved_user_reject_permission_denied(self):
        for rejector_obj, to_reject_obj in itertools.product(
                self.invitations.values(), self.invitations.values()):
            if rejector_obj is to_reject_obj:
                continue

            self._do_reject_permission_denied_test(
                rejector_obj['invitor'], to_reject_obj['invitation'],
                to_reject_obj['url'])
            self._do_reject_permission_denied_test(
                rejector_obj['invitees'][0], to_reject_obj['invitation'],
                to_reject_obj['url'])

    def _do_accept_permission_denied_test(self, user, invitation, accept_url):
        client = MockClient(user)
        response = client.post(accept_url, {})
        self.assertEqual(403, response.status_code)

        loaded = SubmissionGroupInvitation.objects.get(pk=invitation.pk)
        self.assertFalse(user.username in loaded.invitees_who_accepted)

    def _do_reject_permission_denied_test(self, user, invitation, reject_url):
        client = MockClient(user)
        response = client.delete(reject_url, {})
        self.assertEqual(403, response.status_code)

        SubmissionGroupInvitation.objects.get(pk=invitation.pk)
