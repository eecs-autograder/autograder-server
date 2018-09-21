from django.contrib.auth.models import User
from django.db import transaction
from django.utils.decorators import method_decorator
from drf_yasg.openapi import Parameter
from drf_yasg.utils import swagger_auto_schema
from rest_framework import response, status

import autograder.core.models as ag_models
import autograder.rest_api.permissions as ag_permissions
import autograder.rest_api.serializers as ag_serializers
from autograder.rest_api.views.ag_model_views import ListNestedModelViewSet, require_body_params
from autograder.rest_api.views.schema_generation import APITags

_add_handgraders_params = [
    Parameter(
        'new_handgraders',
        'body',
        type='List[string]',
        required=True,
        description='A list of usernames who should be granted handgrader '
                    'privileges for this course.'
    )
]


_remove_handgraders_params = [
    Parameter(
        'remove_handgraders',
        'body',
        type='List[User]',
        required=True,
        description='A list of users whose handgrader privileges '
                    'should be revoked for this course.'
    )
]


class CourseHandgradersViewSet(ListNestedModelViewSet):
    serializer_class = ag_serializers.UserSerializer
    permission_classes = (ag_permissions.is_admin_or_read_only_staff(),)

    model_manager = ag_models.Course.objects
    reverse_to_one_field_name = 'handgraders'

    api_tags = [APITags.permissions]

    @swagger_auto_schema(responses={'204': ''}, request_body_parameters=_add_handgraders_params)
    @transaction.atomic()
    @method_decorator(require_body_params('new_handgraders'))
    def post(self, request, *args, **kwargs):
        course = self.get_object()
        self.add_handgraders(course, request.data['new_handgraders'])

        return response.Response(status=status.HTTP_204_NO_CONTENT)

    @swagger_auto_schema(responses={'204': ''}, request_body_parameters=_remove_handgraders_params)
    @transaction.atomic()
    @method_decorator(require_body_params('remove_handgraders'))
    def patch(self, request, *args, **kwargs):
        course = self.get_object()
        self.remove_handgraders(course, request.data['remove_handgraders'])

        return response.Response(status=status.HTTP_204_NO_CONTENT)

    def add_handgraders(self, course: ag_models.Course, usernames):
        handgraders_to_add = [
            User.objects.get_or_create(username=username)[0]
            for username in usernames]
        course.handgraders.add(*handgraders_to_add)

    def remove_handgraders(self, course: ag_models.Course, users_json):
        handgraders_to_remove = User.objects.filter(
            pk__in=[user['pk'] for user in users_json])
        course.handgraders.remove(*handgraders_to_remove)

    @classmethod
    def as_view(cls, actions=None, **initkwargs):
        return super().as_view(
            actions={'get': 'list', 'post': 'post', 'patch': 'patch'}, **initkwargs)
