import autograder.rest_api.serializers as ag_serializers
import autograder.core.models as ag_models

from .serializer_test_case import SerializerTestCase
import autograder.utils.testing.model_obj_builders as obj_build


class SubmissionGroupInvitationSerializerTestCase(SerializerTestCase):
    def test_serialize(self):
        project = obj_build.build_project(
            project_kwargs={
                'max_group_size': 5,
                'allow_submissions_from_non_enrolled_students': True})
        invitation = ag_models.SubmissionGroupInvitation.objects.validate_and_create(
            obj_build.create_dummy_user(),
            obj_build.create_dummy_users(2),
            project=project)
        self.do_basic_serialize_test(
            invitation,
            ag_serializers.SubmissionGroupInvitationSerializer)
