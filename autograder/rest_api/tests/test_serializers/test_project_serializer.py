import autograder.rest_api.serializers as ag_serializers

from .serializer_test_case import SerializerTestCase
import autograder.core.tests.dummy_object_utils as obj_ut


class ProjectSerializerTestCase(SerializerTestCase):
    def test_serialize(self):
        project = obj_ut.build_project()
        self.do_basic_serialize_test(project, ag_serializers.ProjectSerializer)
