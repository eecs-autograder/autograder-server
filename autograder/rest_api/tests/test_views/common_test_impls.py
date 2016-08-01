"""
The mixin classes defined here provide generic implementations for
common test case patterns.
"""

from django.core import exceptions

from rest_framework import status


class PermissionDeniedGetTest:
    def do_permission_denied_get_test(self, client, user, url, format='json'):
        client.force_authenticate(user)
        response = client.get(url)
        self.assertEqual(status.HTTP_403_FORBIDDEN, response.status_code)

        return response


class ListObjectsTest(PermissionDeniedGetTest):
    def do_list_objects_test(self, client, user, url, expected_data,
                             format='json'):
        client.force_authenticate(user)
        response = client.get(url)
        self.assertEqual(status.HTTP_200_OK, response.status_code)
        self.assertCountEqual(_ordered(expected_data), _ordered(response.data))

        return response


class GetObjectTest(ListObjectsTest):
    def do_get_object_test(self, client, user, url, expected_data,
                           format='json'):
        return self.do_list_objects_test(client, user, url, expected_data)


class CreateObjectInvalidArgsTest:
    def do_invalid_create_object_test(self, model_manager, client,
                                      user, url, request_data, format='json'):
        original_num = model_manager.count()
        client.force_authenticate(user)
        response = client.post(url, request_data, format=format)
        self.assertEqual(status.HTTP_400_BAD_REQUEST, response.status_code)
        self.assertEqual(original_num, model_manager.count())

        return response


class PermissionDeniedCreateTest:
    def do_permission_denied_create_test(self, model_manager, client,
                                         user, url, request_data,
                                         format='json'):
        original_num = model_manager.count()
        client.force_authenticate(user)
        response = client.post(url, request_data, format=format)
        self.assertEqual(status.HTTP_403_FORBIDDEN, response.status_code)
        self.assertEqual(original_num, model_manager.count())

        return response


# TODO: merge mixin methods into this class
class CreateObjectTest(CreateObjectInvalidArgsTest, PermissionDeniedCreateTest):
    def do_create_object_test(self, model_manager, client,
                              user, url, request_data, format='json',
                              check_data=True):
        original_num = model_manager.count()
        client.force_authenticate(user)
        response = client.post(url, request_data, format=format)
        self.assertEqual(status.HTTP_201_CREATED, response.status_code)

        self.assertEqual(original_num + 1, model_manager.count())
        if not check_data:
            return response

        loaded = model_manager.get(pk=response.data['pk'])
        self.assertEqual(_ordered(loaded.to_dict()), _ordered(response.data))

        for arg_name, value in request_data.items():
            actual = getattr(loaded, arg_name)
            try:
                self.assertCountEqual(value, actual)
            except TypeError:
                self.assertEqual(value, actual)

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
        self.assertEqual(_ordered(expected_data),
                         _ordered(ag_model_obj.to_dict()))
        self.assertEqual(_ordered(expected_data), _ordered(response.data))

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
        self.assertEqual(_ordered(expected_data),
                         _ordered(ag_model_obj.to_dict()))
        self.assertEqual(_ordered(expected_data), _ordered(response.data))

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
        self.assertEqual(
            _ordered(expected_data), _ordered(ag_model_obj.to_dict()))

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


# Adapted from: http://stackoverflow.com/questions/25851183/
def _ordered(obj):
    if isinstance(obj, dict):
        return {key: _ordered(value) for key, value in obj.items()}
    if isinstance(obj, list) or isinstance(obj, tuple):
        try:
            return sorted(_ordered(value) for value in obj)
        except TypeError:
            return (_ordered(value) for value in obj)
    else:
        return obj
