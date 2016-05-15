from django import test

import autograder.rest_api.serializers as ag_serializers
import autograder.core.models as ag_models

from .utils import SerializerTestCase
import autograder.core.tests.dummy_object_utils as obj_ut


class SubmissionGroupInvitationSerializerTestCase(SerializerTestCase,
                                                  test.TestCase):
    def setUp(self):
        super().setUp()

    def test_serialize(self):
        project = obj_ut.build_project(
            project_kwargs={
                'max_group_size': 5,
                'allow_submissions_from_non_enrolled_students': True})
        invitation = ag_models.SubmissionGroupInvitation.objects.validate_and_create(
            obj_ut.create_dummy_user(),
            obj_ut.create_dummy_users(2),
            project=project)
        self.do_basic_serialize_test(
            invitation,
            ag_serializers.SubmissionGroupInvitationSerializer)
