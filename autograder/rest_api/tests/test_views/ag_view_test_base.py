"""
The mixin classes defined here provide generic implementations for
common test case patterns.
"""

from django.core import exceptions

from rest_framework import status

from autograder import utils
from autograder.utils.testing import UnitTestBase


class AGViewTestBase(UnitTestBase):
    def do_permission_denied_get_test(self, client, user, url, format='json'):
        client.force_authenticate(user)
        response = client.get(url)
        self.assertEqual(status.HTTP_403_FORBIDDEN, response.status_code)

        return response

    def do_list_objects_test(self, client, user, url, expected_data, *,
                             check_order=False):
        client.force_authenticate(user)
        response = client.get(url)
        self.assertEqual(status.HTTP_200_OK, response.status_code)
        if check_order:
            self.assertSequenceEqual(expected_data, response.data)
        else:
            self.assert_list_contents_equal(expected_data, response.data)

        return response

    def do_get_object_test(self, client, user, url, expected_data):
        return self.do_list_objects_test(client, user, url, expected_data)

    def do_get_request_404_test(self, client, user, url):
        client.force_authenticate(user)
        response = client.get(url)
        self.assertEqual(status.HTTP_404_NOT_FOUND, response.status_code)

    def do_invalid_create_object_test(self, model_manager, client,
                                      user, url, request_data, format='json'):
        original_num = model_manager.count()
        client.force_authenticate(user)
        response = client.post(url, request_data, format=format)
        self.assertEqual(status.HTTP_400_BAD_REQUEST, response.status_code)
        self.assertEqual(original_num, model_manager.count())

        return response

    def do_permission_denied_create_test(self, model_manager, client,
                                         user, url, request_data,
                                         format='json'):
        original_num = model_manager.count()
        client.force_authenticate(user)
        response = client.post(url, request_data, format=format)
        self.assertEqual(status.HTTP_403_FORBIDDEN, response.status_code)
        self.assertEqual(original_num, model_manager.count())

        return response

    def do_create_object_test(self, model_manager, client,
                              user, url, request_data, format='json',
                              check_data=True):
        original_num = model_manager.count()
        client.force_authenticate(user)
        response = client.post(url, request_data, format=format)
        self.assertEqual(status.HTTP_201_CREATED, response.status_code, msg=response.data)

        self.assertEqual(original_num + 1, model_manager.count())
        if not check_data:
            return response

        loaded = model_manager.get(pk=response.data['pk'])
        self.assert_dict_contents_equal(loaded.to_dict(), response.data)

        for arg_name, value in request_data.items():
            # TODO: This fails if request_data has foreign keys
            # IDEA: actual = loaded.to_dict()[arg_name]
            actual = getattr(loaded, arg_name)
            try:
                self.assertCountEqual(value, actual)
            except TypeError:
                self.assertEqual(value, actual)

        return response

    def do_patch_object_test(self, ag_model_obj, client, user, url,
                             request_data, format='json',
                             ignore_fields=[]):
        ignore_fields = list(ignore_fields)
        ignore_fields.append('last_modified')

        expected_data = ag_model_obj.to_dict()
        for field in ignore_fields:
            expected_data.pop(field, None)
        for key, value in request_data.items():
            if isinstance(value, dict):
                expected_data[key].update(value)
            else:
                expected_data[key] = value

        client.force_authenticate(user)
        response = client.patch(url, request_data, format=format)
        self.assertEqual(status.HTTP_200_OK, response.status_code)

        ag_model_obj = ag_model_obj._meta.model.objects.get(pk=ag_model_obj.pk)
        self.assert_dict_contents_equal(
            expected_data, utils.exclude_dict(ag_model_obj.to_dict(), ignore_fields))
        self.assert_dict_contents_equal(
            expected_data, utils.exclude_dict(response.data, ignore_fields))

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
        expected_data.pop('last_modified', None)
        expected_data.update(request_data)

        client.force_authenticate(user)
        response = client.put(url, request_data, format=format)
        self.assertEqual(status.HTTP_200_OK, response.status_code)

        ag_model_obj = ag_model_obj._meta.model.objects.get(pk=ag_model_obj.pk)
        self.assert_dict_contents_equal(
            expected_data, utils.exclude_dict(ag_model_obj.to_dict(), 'last_modified'))
        self.assert_dict_contents_equal(
            expected_data, utils.exclude_dict(response.data, 'last_modified'))

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

        ag_model_obj = ag_model_obj._meta.model.objects.get(pk=ag_model_obj.pk)
        self.assert_dict_contents_equal(expected_data, ag_model_obj.to_dict())

        return response

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


class PermissionDeniedGetTest(AGViewTestBase):
    pass


class ListObjectsTest(AGViewTestBase):
    pass


class GetObjectTest(AGViewTestBase):
    pass


class CreateObjectInvalidArgsTest(AGViewTestBase):
    pass


class PermissionDeniedCreateTest(AGViewTestBase):
    pass


class CreateObjectTest(AGViewTestBase):
    pass


class UpdateObjectTest(AGViewTestBase):
    pass


class DestroyObjectTest(AGViewTestBase):
    pass
