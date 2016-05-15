from django import test

import autograder.rest_api.serializers as ag_serializers

from .utils import SerializerTestCase
import autograder.core.tests.dummy_object_utils as obj_ut


class SubmissionGroupSerializerTestCase(SerializerTestCase, test.TestCase):
    def setUp(self):
        super().setUp()

    def test_serialize(self):
        group = obj_ut.build_submission_group()
        self.do_basic_serialize_test(group,
                                     ag_serializers.SubmissionGroupSerializer)
