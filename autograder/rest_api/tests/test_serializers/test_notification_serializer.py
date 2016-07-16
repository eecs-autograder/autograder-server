import autograder.rest_api.serializers as ag_serializers
import autograder.core.models as ag_models

from .serializer_test_case import SerializerTestCase
import autograder.core.tests.dummy_object_utils as obj_ut


class NotificationSerializerTestCase(SerializerTestCase):
    def test_serialize(self):
        notification = ag_models.Notification.objects.validate_and_create(
            message='spamspamspam',
            recipient=obj_ut.create_dummy_user())
        self.do_basic_serialize_test(notification,
                                     ag_serializers.NotificationSerializer)
