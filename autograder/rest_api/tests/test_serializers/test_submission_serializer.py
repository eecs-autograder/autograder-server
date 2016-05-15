from django import test

import autograder.rest_api.serializers as ag_serializers
import autograder.core.models as ag_models

from .utils import SerializerTestCase
import autograder.core.tests.dummy_object_utils as obj_ut


class SubmissionSerializerTestCase(SerializerTestCase, test.TestCase):
    def setUp(self):
        super().setUp()

    def test_serialize(self):
        group = obj_ut.build_submission_group()
        submission = ag_models.Submission.objects.validate_and_create(
            submitted_files=[],
            submission_group=group)
        self.do_basic_serialize_test(submission,
                                     ag_serializers.SubmissionSerializer)
