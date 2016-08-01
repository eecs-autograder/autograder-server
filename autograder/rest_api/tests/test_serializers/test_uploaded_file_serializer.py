from django.core.files.uploadedfile import SimpleUploadedFile

import autograder.rest_api.serializers as ag_serializers
import autograder.core.models as ag_models

from .serializer_test_case import SerializerTestCase
import autograder.utils.testing.model_obj_builders as obj_build


class UploadedFileSerializerTestCase(SerializerTestCase):
    def test_serialize(self):
        project = obj_build.build_project()
        uploaded_file = ag_models.UploadedFile.objects.validate_and_create(
            file_obj=SimpleUploadedFile('spam', b'waaaaluigi'),
            project=project
        )
        self.do_basic_serialize_test(uploaded_file,
                                     ag_serializers.UploadedFileSerializer)
