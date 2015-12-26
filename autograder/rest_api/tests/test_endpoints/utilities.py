import json

from django.core.serializers.json import DjangoJSONEncoder
from django.test import RequestFactory
from django.core.urlresolvers import resolve

from autograder.core.tests.temporary_filesystem_test_case import (
    TemporaryFilesystemTestCase)

import autograder.core.tests.dummy_object_utils as obj_ut


class RequestHandlerTestCase(TemporaryFilesystemTestCase):
    def assertJSONObjsEqual(self, json1, json2):
        self.assertEqual(
            json.dumps(json1, sort_keys=True, indent=4, cls=DjangoJSONEncoder),
            json.dumps(json2, sort_keys=True, indent=4, cls=DjangoJSONEncoder))


def json_load_bytes(data):
    return json.loads(data.decode('utf-8'))


def sorted_by_pk(iterable):
    return sorted(iterable, key=lambda obj: obj.pk)


class MockClient:
    def __init__(self, user):
        self.request_factory = RequestFactory()
        self.user = user

    def get(self, url, query_params={}):
        request = self.request_factory.get(url, query_params)
        request.user = self.user

        resolved = resolve(request.path)
        return resolved.func(request, *resolved.args, **resolved.kwargs)

    def post(self, url, data):
        request = self.request_factory.post(
            url, json.dumps(data, cls=DjangoJSONEncoder),
            content_type='application/json')
        request.user = self.user

        resolved = resolve(request.path)
        return resolved.func(request, *resolved.args, **resolved.kwargs)

    def patch(self, url, data):
        request = self.request_factory.patch(
            url, json.dumps(data, cls=DjangoJSONEncoder))
        request.user = self.user

        resolved = resolve(request.path)
        return resolved.func(request, *resolved.args, **resolved.kwargs)

    def delete(self, url, data={}):
        request = self.request_factory.delete(
            url, json.dumps(data, cls=DjangoJSONEncoder))
        request.user = self.user

        resolved = resolve(request.path)
        return resolved.func(request, *resolved.args, **resolved.kwargs)

# -----------------------------------------------------------------------------
# -----------------------------------------------------------------------------


# class TestingData:
#     def __init__(self):
#         self.project = obj_ut.build_project


