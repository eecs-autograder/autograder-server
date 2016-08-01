import autograder.rest_api.serializers as ag_serializers

from .serializer_test_case import SerializerTestCase
import autograder.utils.testing.model_obj_builders as obj_build


class SubmissionGroupSerializerTestCase(SerializerTestCase):
    def test_serialize(self):
        group = obj_build.build_submission_group()
        self.do_basic_serialize_test(group,
                                     ag_serializers.SubmissionGroupSerializer)
