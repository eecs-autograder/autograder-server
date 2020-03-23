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

# _add_students_params = [
#     Parameter(
#         'new_students',
#         'body',
#         type='List[string]',
#         required=True,
#         description='A list of usernames who should be granted student '
#                     'privileges for this course.'
#     )
# ]


# _remove_students_params = [
#     Parameter(
#         'remove_students',
#         'body',
#         type='List[User]',
#         required=True,
#         description='A list of users whose student privileges '
#                     'should be revoked for this course.'
#     )
# ]


class CourseStudentsViewSet(ListNestedModelViewSet):
    serializer_class = ag_serializers.UserSerializer
    permission_classes = (ag_permissions.is_admin_or_read_only_staff(),)

    model_manager = ag_models.Course.objects
    reverse_to_one_field_name = 'students'

    api_tags = [APITags.permissions]

    # @swagger_auto_schema(responses={'204': ''}, request_body_parameters=_add_students_params)
    @transaction.atomic()
    @method_decorator(require_body_params('new_students'))
    def post(self, request, *args, **kwargs):
        course = self.get_object()
        self.add_students(course, request.data['new_students'])

        clear_cached_user_roles(course.pk)
        return response.Response(status=status.HTTP_204_NO_CONTENT)

    # @swagger_auto_schema(responses={'204': ''}, request_body_parameters=_add_students_params)
    @transaction.atomic()
    @method_decorator(require_body_params('new_students'))
    def put(self, request, *args, **kwargs):
        """
        Completely REPLACES the student roster with the one included in
        the request.
        """
        new_roster = [
            User.objects.get_or_create(username=username)[0]
            for username in request.data['new_students']
        ]
        course = self.get_object()
        course.students.set(new_roster, clear=True)

        clear_cached_user_roles(course.pk)
        return response.Response(status=status.HTTP_204_NO_CONTENT)

    # @swagger_auto_schema(responses={'204': ''}, request_body_parameters=_remove_students_params)
    @transaction.atomic()
    @method_decorator(require_body_params('remove_students'))
    def patch(self, request, *args, **kwargs):
        course = self.get_object()
        self.remove_students(course, request.data['remove_students'])

        clear_cached_user_roles(course.pk)
        return response.Response(status=status.HTTP_204_NO_CONTENT)

    def add_students(self, course: ag_models.Course, usernames):
        students_to_add = [
            User.objects.get_or_create(username=username)[0]
            for username in usernames]
        course.students.add(*students_to_add)

    def remove_students(self, course: ag_models.Course, users_json):
        students_to_remove = User.objects.filter(
            pk__in=[user['pk'] for user in users_json])
        course.students.remove(*students_to_remove)

    @classmethod
    def as_view(cls, actions=None, **initkwargs):
        return super().as_view(
            actions={'get': 'list', 'post': 'post', 'patch': 'patch', 'put': 'put'}, **initkwargs)
