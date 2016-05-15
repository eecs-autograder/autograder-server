from django import test

import autograder.rest_api.serializers as ag_serializers
import autograder.core.models as ag_models

from .utils import SerializerTestCase
import autograder.core.tests.dummy_object_utils as obj_ut


class ExpectedStudentFilePatternSerializerTestCase(SerializerTestCase,
                                                   test.TestCase):
    def setUp(self):
        super().setUp()

    def test_serialize(self):
        project = obj_ut.build_project()
        pattern = (
            ag_models.ExpectedStudentFilePattern.objects.validate_and_create(
                pattern='spam',
                project=project))
        self.do_basic_serialize_test(
            pattern, ag_serializers.ExpectedStudentFilePatternSerializer)
