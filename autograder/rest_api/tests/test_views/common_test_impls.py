"""
The mixin classes defined here provide generic implementations for
commonly used test cases.
"""

from django.core import exceptions

from rest_framework import status


class ListObjectsTest:
    def do_list_objects_test(self, client, user, url, expected_data):
        client.force_authenticate(user)
        response = client.get(url)
        self.assertEqual(status.HTTP_200_OK, response.status_code)
        self.assertCountEqual(expected_data, response.data)

        return response


class PermissionDeniedGetTest:
    def do_permission_denied_get_test(self, client, user, url):
        client.force_authenticate(user)
        response = client.get(url)
        self.assertEqual(status.HTTP_403_FORBIDDEN, response.status_code)

        return response


class GetObjectTest(ListObjectsTest, PermissionDeniedGetTest):
    def do_get_object_test(self, client, user, url, expected_data):
        return self.do_list_objects_test(client, user, url, expected_data)


class CreateObjectTest:
    def do_create_object_test(self, model_manager, client,
                              user, url, request_data, format='json'):
        self.assertEqual(0, model_manager.count())
        client.force_authenticate(user)
        response = client.post(url, request_data, format=format)
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

        return response


class CreateObjectInvalidArgsTest:
    def do_invalid_create_object_test(self, model_manager, client,
                                      user, url, request_data, format='json'):
        self.assertEqual(0, model_manager.count())
        client.force_authenticate(user)
        response = client.post(url, request_data, format=format)
        self.assertEqual(status.HTTP_400_BAD_REQUEST, response.status_code)
        self.assertEqual(0, model_manager.count())

        return response


class PermissionDeniedCreateTest:
    def do_permission_denied_create_test(self, model_manager, client,
                                         user, url, request_data,
                                         format='json'):
        self.assertEqual(0, model_manager.count())
        client.force_authenticate(user)
        response = client.post(url, request_data, format=format)
        self.assertEqual(status.HTTP_403_FORBIDDEN, response.status_code)
        self.assertEqual(0, model_manager.count())

        return response


class UpdateObjectTest:
    def do_patch_object_test(self, ag_model_obj, client, user, url,
                             request_data, format='json'):
        expected_data = ag_model_obj.to_dict()
        expected_data.update(request_data)

        client.force_authenticate(user)
        response = client.patch(url, request_data, format=format)
        self.assertEqual(status.HTTP_200_OK, response.status_code)

        ag_model_obj.refresh_from_db()
        self.assertEqual(expected_data, ag_model_obj.to_dict())
        self.assertEqual(expected_data, response.data)

        return response

    def do_patch_object_invalid_args_test(self, ag_model_obj, client, user,
                                          url, request_data, format='json'):
        return self._do_bad_update_test(
            ag_model_obj, client, user, url, request_data, client.patch,
            status.HTTP_400_BAD_REQUEST, format=format)

    def do_patch_object_permission_denied_test(self, ag_model_obj, client,
                                               user, url, request_data,
                                               format='json'):
        return self._do_bad_update_test(
            ag_model_obj, client, user, url, request_data, client.patch,
            status.HTTP_403_FORBIDDEN, format=format)

    def do_put_object_test(self, ag_model_obj, client, user, url,
                           request_data, format='json'):
        expected_data = ag_model_obj.to_dict()
        expected_data.update(request_data)

        client.force_authenticate(user)
        response = client.put(url, request_data, format=format)
        self.assertEqual(status.HTTP_200_OK, response.status_code)

        ag_model_obj.refresh_from_db()
        self.assertEqual(expected_data, ag_model_obj.to_dict())
        self.assertEqual(expected_data, response.data)

        return response

    def do_put_object_invalid_args_test(self, ag_model_obj, client, user, url,
                                        request_data, format='json'):
        return self._do_bad_update_test(
            ag_model_obj, client, user, url, request_data, client.put,
            status.HTTP_400_BAD_REQUEST, format=format)

    def do_put_object_permission_denied_test(self, ag_model_obj, client, user,
                                             url, request_data, format='json'):
        return self._do_bad_update_test(
            ag_model_obj, client, user, url, request_data, client.put,
            status.HTTP_403_FORBIDDEN, format=format)

    def _do_bad_update_test(self, ag_model_obj, client, user, url, request_data,
                            client_method, expected_status, format='json'):
        expected_data = ag_model_obj.to_dict()

        client.force_authenticate(user)
        response = client_method(url, request_data, format=format)
        self.assertEqual(expected_status, response.status_code)

        ag_model_obj.refresh_from_db()
        self.assertEqual(expected_data, ag_model_obj.to_dict())

        return response


class DestroyObjectTest:
    def do_delete_object_test(self, ag_model_obj, client, user, url):
        client.force_authenticate(user)
        response = client.delete(url)
        self.assertEqual(status.HTTP_204_NO_CONTENT, response.status_code)
        with self.assertRaises(exceptions.ObjectDoesNotExist):
            ag_model_obj.refresh_from_db()

        return response

    def do_delete_object_permission_denied_test(self, ag_model_obj, client,
                                                user, url):
        client.force_authenticate(user)
        response = client.delete(url)
        self.assertEqual(status.HTTP_403_FORBIDDEN, response.status_code)
        ag_model_obj.refresh_from_db()

        return response
