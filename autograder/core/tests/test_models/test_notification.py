import autograder.core.models as ag_models

from autograder.core.tests.temporary_filesystem_test_case import (
    TemporaryFilesystemTestCase)

import autograder.core.tests.dummy_object_utils as obj_ut


class NotificationTestCase(TemporaryFilesystemTestCase):
    def setUp(self):
        super().setUp()

    def test_to_dict_default_fields(self):
        expected_fields = [
            'timestamp',
            'message',
            'recipient',
        ]

        self.assertCountEqual(
            expected_fields,
            ag_models.Notification.get_default_to_dict_fields())

        notification = ag_models.Notification.objects.validate_and_create(
            message='waaaaaaaaaluigi',
            recipient=obj_ut.create_dummy_user())
        self.assertTrue(notification.to_dict())

    def test_editable_fields(self):
        self.assertCountEqual([], ag_models.Notification.get_editable_fields())
