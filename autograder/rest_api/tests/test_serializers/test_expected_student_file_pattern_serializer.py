import autograder.rest_api.serializers as ag_serializers
import autograder.core.models as ag_models

from .serializer_test_case import SerializerTestCase
import autograder.core.tests.dummy_object_utils as obj_ut


class ExpectedStudentFilePatternSerializerTestCase(SerializerTestCase):
    def test_serialize(self):
        project = obj_ut.build_project()
        pattern = (
            ag_models.ExpectedStudentFilePattern.objects.validate_and_create(
                pattern='spam',
                project=project))
        self.do_basic_serialize_test(
            pattern, ag_serializers.ExpectedStudentFilePatternSerializer)
