from django.core.files.uploadedfile import SimpleUploadedFile
from django.http import QueryDict

import autograder.rest_api.serializers as ag_serializers
import autograder.core.models as ag_models

from .serializer_test_case import SerializerTestCase
import autograder.core.tests.dummy_object_utils as obj_ut


class SubmissionSerializerTestCase(SerializerTestCase):
    def test_serialize(self):
        group = obj_ut.build_submission_group()
        submission = ag_models.Submission.objects.validate_and_create(
            submitted_files=[],
            submission_group=group)
        self.do_basic_serialize_test(submission,
                                     ag_serializers.SubmissionSerializer)

    def test_create(self):
        files = [SimpleUploadedFile('spam', b'spammo'),
                 SimpleUploadedFile('egg', b'waaaaluigi')]
        data = QueryDict(mutable=True)
        data['submission_group'] = obj_ut.build_submission_group()
        # We are adding the files one at a time because of the way that
        # QueryDict appends values to lists
        for file_ in files:
            data.update({'submitted_files': file_})
        # Sanity check for data contents
        self.assertCountEqual(files, data.getlist('submitted_files'))
        self.assertEqual(QueryDict, type(data))

        serializer = ag_serializers.SubmissionSerializer(data=data)
        serializer.is_valid()
        serializer.save()

        self.assertEqual(1, ag_models.Submission.objects.count())
        loaded = ag_models.Submission.objects.first()

        self.assertCountEqual(
            (file_.name for file_ in files), loaded.discarded_files)
