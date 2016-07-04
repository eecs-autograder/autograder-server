"""
The mixin classes defined here provide generic implementations for
commonly used test cases.
"""

from rest_framework import status


class ListObjectsTest:
    def do_list_objects_test(self, client, user, url, expected_data):
        client.force_authenticate(user)
        response = client.get(url)
        self.assertEqual(status.HTTP_200_OK, response.status_code)
        self.assertCountEqual(expected_data, response.data)


class PermissionDeniedGetTest:
    def do_permission_denied_get_test(self, client, user, url):
        client.force_authenticate(user)
        response = client.get(url)
        self.assertEqual(status.HTTP_403_FORBIDDEN, response.status_code)


class CreateObjectTest:
    def do_create_object_test(self, model_manager, client,
                              user, url, request_data):
        self.assertEqual(0, model_manager.count())
        client.force_authenticate(user)
        response = client.post(url, request_data)
        self.assertEqual(status.HTTP_201_CREATED, response.status_code)

        self.assertEqual(1, model_manager.count())
        loaded = model_manager.first()
        self.assertEqual(loaded.to_dict(), response.data)

        for arg_name, value in request_data.items():
            actual = getattr(loaded, arg_name)
            try:
                self.assertCountEqual(value, actual)
            except TypeError:
                self.assertEqual(value, actual)


class CreateObjectInvalidArgsTest:
    def do_invalid_create_object_test(self, model_manager, client,
                                      user, url, request_data):
        self.assertEqual(0, model_manager.count())
        client.force_authenticate(user)
        response = client.post(url, request_data)
        self.assertEqual(status.HTTP_400_BAD_REQUEST, response.status_code)
        self.assertEqual(0, model_manager.count())

        return response


class PermissionDeniedCreateTest:
    def do_permission_denied_create_test(self, model_manager, client,
                                         user, url, request_data):
        self.assertEqual(0, model_manager.count())
        client.force_authenticate(user)
        response = client.post(url, request_data)
        self.assertEqual(status.HTTP_403_FORBIDDEN, response.status_code)
        self.assertEqual(0, model_manager.count())
