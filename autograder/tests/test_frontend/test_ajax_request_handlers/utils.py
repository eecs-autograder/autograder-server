import json

from django.core.serializers.json import DjangoJSONEncoder
from django.test import RequestFactory
from django.core.urlresolvers import resolve


def json_load_bytes(data):
    return json.loads(data.decode('utf-8'))


_REQUEST_FACTORY = RequestFactory()


def process_get_request(url, user):
    request = _REQUEST_FACTORY.get(url)
    request.user = user

    resolved = resolve(request.path)
    return resolved.func(request, *resolved.args, **resolved.kwargs)


def process_post_request(url, data, user):
    request = _REQUEST_FACTORY.post(
        url, json.dumps(data, cls=DjangoJSONEncoder),
        content_type='application/json')
    request.user = user

    resolved = resolve(request.path)
    return resolved.func(request, *resolved.args, **resolved.kwargs)


def process_patch_request(url, data, user):
    request = _REQUEST_FACTORY.patch(
        url, json.dumps(data, cls=DjangoJSONEncoder))
    request.user = user

    resolved = resolve(request.path)
    return resolved.func(request, *resolved.args, **resolved.kwargs)


def process_delete_request(url, user):
    request = _REQUEST_FACTORY.delete(url)
    request.user = user

    resolved = resolve(request.path)
    return resolved.func(request, *resolved.args, **resolved.kwargs)
