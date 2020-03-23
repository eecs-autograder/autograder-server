from django.contrib.auth.models import User
from django.db import transaction
from django.utils.decorators import method_decorator
# from drf_yasg.openapi import Parameter
# from drf_yasg.utils import swagger_auto_schema
from rest_framework import response, status

import autograder.core.models as ag_models
import autograder.rest_api.permissions as ag_permissions
import autograder.rest_api.serializers as ag_serializers
from autograder.core.models.course import clear_cached_user_roles
from autograder.rest_api.views.ag_model_views import ListNestedModelViewSet, require_body_params
from autograder.rest_api.views.schema_generation import APITags

# _add_staff_params = [
#     Parameter(
#         'new_staff',
#         'body',
#         type='List[string]',
#         required=True,
#         description='A list of usernames who should be granted staff '
#                     'privileges for this course.'
#     )
# ]


# _remove_staff_params = [
#     Parameter(
#         'remove_staff',
#         'body',
#         type='List[User]',
#         required=True,
#         description='A list of users whose staff privileges '
#                     'should be revoked for this course.'
#     )
# ]


class CourseStaffViewSet(ListNestedModelViewSet):
    serializer_class = ag_serializers.UserSerializer
    permission_classes = (ag_permissions.is_admin_or_read_only_staff_or_handgrader(),)

    model_manager = ag_models.Course.objects
    reverse_to_one_field_name = 'staff'

    api_tags = [APITags.permissions]

    # @swagger_auto_schema(responses={'204': ''}, request_body_parameters=_add_staff_params)
    @transaction.atomic()
    @method_decorator(require_body_params('new_staff'))
    def post(self, request, *args, **kwargs):
        course = self.get_object()
        self.add_staff(course, request.data['new_staff'])

        clear_cached_user_roles(course.pk)
        return response.Response(status=status.HTTP_204_NO_CONTENT)

    # @swagger_auto_schema(responses={'204': ''}, request_body_parameters=_remove_staff_params)
    @transaction.atomic()
    @method_decorator(require_body_params('remove_staff'))
    def patch(self, request, *args, **kwargs):
        course = self.get_object()
        self.remove_staff(course, request.data['remove_staff'])

        clear_cached_user_roles(course.pk)
        return response.Response(status=status.HTTP_204_NO_CONTENT)

    def add_staff(self, course, usernames):
        staff_to_add = [
            User.objects.get_or_create(username=username)[0]
            for username in usernames]
        course.staff.add(*staff_to_add)

    def remove_staff(self, course, users_json):
        staff_to_remove = User.objects.filter(
            pk__in=[user['pk'] for user in users_json])
        course.staff.remove(*staff_to_remove)

    @classmethod
    def as_view(cls, actions=None, **initkwargs):
        return super().as_view(
            actions={'get': 'list', 'post': 'post', 'patch': 'patch'}, **initkwargs)
