import autograder.rest_api.serializers as ag_serializers
import autograder.core.models as ag_models

from .serializer_test_case import SerializerTestCase
import autograder.utils.testing.model_obj_builders as obj_build


class ExpectedStudentFilePatternSerializerTestCase(SerializerTestCase):
    def test_serialize(self):
        project = obj_build.build_project()
        pattern = (
            ag_models.ExpectedStudentFilePattern.objects.validate_and_create(
                pattern='spam',
                project=project))
        self.do_basic_serialize_test(
            pattern, ag_serializers.ExpectedStudentFilePatternSerializer)
