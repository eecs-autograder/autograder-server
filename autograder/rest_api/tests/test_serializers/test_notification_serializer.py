import autograder.rest_api.serializers as ag_serializers
import autograder.core.models as ag_models

from .serializer_test_case import SerializerTestCase
import autograder.utils.testing.model_obj_builders as obj_build


class NotificationSerializerTestCase(SerializerTestCase):
    def test_serialize(self):
        notification = ag_models.Notification.objects.validate_and_create(
            message='spamspamspam',
            recipient=obj_build.create_dummy_user())
        self.do_basic_serialize_test(notification,
                                     ag_serializers.NotificationSerializer)
