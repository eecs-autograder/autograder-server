from django import test
from django.contrib.auth.models import User

from autograder.rest_api.serializers.user_serializer import UserSerializer

import autograder.core.tests.dummy_object_utils as obj_ut


_EXPECTED_USER_FIELDS = [
    'pk',
    'username',
    'first_name',
    'last_name',
    'email'
]


def _user_to_expected_dict(user):
    return {field: getattr(user, field) for field in _EXPECTED_USER_FIELDS}


class UserSerializerTestCase(test.TestCase):
    def setUp(self):
        self.user = obj_ut.create_dummy_user()

    def test_serialize_user(self):
        serializer = UserSerializer(self.user)
        self.assertEqual(_user_to_expected_dict(self.user), serializer.data)

    def test_create_user(self):
        data = _user_to_expected_dict(self.user)
        data.pop('pk')
        data['username'] = 'stove'

        serializer = UserSerializer(data=data)
        serializer.is_valid()
        serializer.save()

        self.assertEqual(2, User.objects.count())

    def test_update_user(self):
        new_username = 'steve'
        serializer = UserSerializer(self.user,
                                    data={'username': new_username},
                                    partial=True)
        serializer.is_valid()
        serializer.save()

        self.user.refresh_from_db()
        self.assertEqual(new_username, self.user.username)
