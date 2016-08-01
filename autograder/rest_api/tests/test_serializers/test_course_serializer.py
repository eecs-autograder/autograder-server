import autograder.rest_api.serializers as ag_serializers

from .serializer_test_case import SerializerTestCase
import autograder.utils.testing.model_obj_builders as obj_build


class CourseSerializerTestCase(SerializerTestCase):
    def setUp(self):
        super().setUp()

    def test_serialize(self):
        course = obj_build.build_course()
        self.do_basic_serialize_test(course, ag_serializers.CourseSerializer)
