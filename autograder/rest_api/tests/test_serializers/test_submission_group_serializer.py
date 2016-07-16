import autograder.rest_api.serializers as ag_serializers

from .serializer_test_case import SerializerTestCase
import autograder.core.tests.dummy_object_utils as obj_ut


class SubmissionGroupSerializerTestCase(SerializerTestCase):
    def test_serialize(self):
        group = obj_ut.build_submission_group()
        self.do_basic_serialize_test(group,
                                     ag_serializers.SubmissionGroupSerializer)
