import itertools

from django.core.urlresolvers import reverse

from autograder.core.tests.temporary_filesystem_test_case import (
    TemporaryFilesystemTestCase)
import autograder.core.tests.dummy_object_utils as obj_ut
from .utilities import MockClient, json_load_bytes, sorted_by_pk


class GetAcceptRejectSubmissionGroupInvitationTestCase(TemporaryFilesystemTestCase):
    def setUp(self):
        super().setUp()

    def test_invitation_creator_view_invitation(self):
        self.fail()

    def test_invitee_view_invitation(self):
        self.fail()

    def test_other_view_invitation_permission_denied(self):
        self.fail()

    def test_view_invitation_user_cannot_view_project_permission_denied(self):
        self.fail()

    # -------------------------------------------------------------------------

    def test_all_invitees_accept_invitation(self):
        self.fail()

    def test_invitee_reject_invitation(self):
        self.fail()

    def test_some_invitees_accept_one_rejects(self):
        self.fail()

    def test_invitation_creator_revokes_invitation(self):
        self.fail()

    def test_accept_invitation_cannot_view_project_permission_denied(self):
        self.fail()

    def test_reject_invitation_cannot_view_project_permission_denied(self):
        self.fail()
