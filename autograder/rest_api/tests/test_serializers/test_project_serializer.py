from django import test

import autograder.rest_api.serializers as ag_serializers

from .utils import SerializerTestCase
import autograder.core.tests.dummy_object_utils as obj_ut


class ProjectSerializerTestCase(SerializerTestCase, test.TestCase):
    def setUp(self):
        super().setUp()

    def test_serialize(self):
        project = obj_ut.build_project()
        self.do_basic_serialize_test(project, ag_serializers.ProjectSerializer)
