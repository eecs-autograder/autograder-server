import autograder.rest_api.serializers as ag_serializers

from .serializer_test_case import SerializerTestCase
import autograder.core.tests.dummy_object_utils as obj_ut


class CourseSerializerTestCase(SerializerTestCase):
    def setUp(self):
        super().setUp()

    def test_serialize(self):
        course = obj_ut.build_course()
        self.do_basic_serialize_test(course, ag_serializers.CourseSerializer)
