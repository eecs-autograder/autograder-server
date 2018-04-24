from django.contrib.auth.models import User
from django.db import transaction
from django.utils.decorators import method_decorator
from drf_composable_permissions.p import P
from drf_yasg.openapi import Parameter
from drf_yasg.utils import swagger_auto_schema
from rest_framework import response, status, exceptions

import autograder.core.models as ag_models
import autograder.rest_api.permissions as ag_permissions
import autograder.rest_api.serializers as ag_serializers
from autograder.rest_api.views.ag_model_views import ListNestedModelViewSet, require_body_params
from autograder.rest_api.views.schema_generation import APITags

_add_admins_params = [
    Parameter(
        'new_admins',
        'body',
        type='List[string]',
        required=True,
        description='A list of usernames who should be granted admin '
                    'privileges for this course.'
    )
]


_remove_admins_params = [
    Parameter(
        'remove_admins',
        'body',
        type='List[User]',
        required=True,
        description='A list of users whose admin privileges '
                    'should be revoked for this course.'
    )
]


class CourseAdminViewSet(ListNestedModelViewSet):
    serializer_class = ag_serializers.UserSerializer
    permission_classes = (
        P(ag_permissions.IsSuperuser) | P(ag_permissions.is_admin_or_read_only_staff()),)

    model_manager = ag_models.Course.objects
    reverse_to_one_field_name = 'admins'

    api_tags = [APITags.permissions]

    @swagger_auto_schema(responses={'204': ''}, request_body_parameters=_add_admins_params)
    @transaction.atomic()
    @method_decorator(require_body_params('new_admins'))
    def post(self, request, *args, **kwargs):
        course = self.get_object()
        self.add_admins(course, request.data['new_admins'])

        return response.Response(status=status.HTTP_204_NO_CONTENT)

    @swagger_auto_schema(responses={'204': ''}, request_body_parameters=_remove_admins_params)
    @transaction.atomic()
    @method_decorator(require_body_params('remove_admins'))
    def patch(self, request, *args, **kwargs):
        course = self.get_object()
        self.remove_admins(course, request.data['remove_admins'])

        return response.Response(status=status.HTTP_204_NO_CONTENT)

    def add_admins(self, course: ag_models.Course, usernames):
        users_to_add = [
            User.objects.get_or_create(username=username)[0]
            for username in usernames]
        course.admins.add(*users_to_add)

    def remove_admins(self, course: ag_models.Course, users_json):
        users_to_remove = User.objects.filter(pk__in=[user['pk'] for user in users_json])

        if self.request.user in users_to_remove:
            raise exceptions.ValidationError(
                {'remove_admins': ["You cannot remove your own admin privileges."]})

        course.admins.remove(*users_to_remove)
