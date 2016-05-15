from django import test

import autograder.rest_api.serializers as ag_serializers

from .utils import SerializerTestCase
import autograder.core.tests.dummy_object_utils as obj_ut


class SemesterSerializerTestCase(SerializerTestCase, test.TestCase):
    def setUp(self):
        super().setUp()

    def test_serialize(self):
        semester = obj_ut.build_semester()
        self.do_basic_serialize_test(semester,
                                     ag_serializers.SemesterSerializer)
