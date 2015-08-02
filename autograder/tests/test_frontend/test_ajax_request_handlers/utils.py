import json

from django.test import RequestFactory
from django.core.urlresolvers import resolve


def json_load_bytes(data):
    return json.loads(data.decode('utf-8'))


def process_get_request(url, user):
    rf = RequestFactory()

    request = rf.get(url)
    request.user = user

    resolved = resolve(request.path)
    return resolved.func(request, *resolved.args, **resolved.kwargs)


def process_post_request(url, data, user):
    rf = RequestFactory()

    request = rf.post(url, json.dumps(data), content_type='application/json')
    request.user = user

    resolved = resolve(request.path)
    return resolved.func(request, *resolved.args, **resolved.kwargs)


def process_patch_request(url, data, user):
    rf = RequestFactory()

    request = rf.patch(url, json.dumps(data))
    request.user = user

    resolved = resolve(request.path)
    return resolved.func(request, *resolved.args, **resolved.kwargs)
