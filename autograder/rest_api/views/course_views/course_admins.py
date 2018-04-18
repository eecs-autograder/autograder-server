from django.contrib.auth.models import User
from django.db import transaction
from drf_composable_permissions.p import P

from rest_framework import response, status, exceptions

import autograder.core.models as ag_models
import autograder.rest_api.permissions as ag_permissions
import autograder.rest_api.serializers as ag_serializers
from autograder.rest_api.views.ag_model_views import ListNestedModelViewSet


class CourseAdminViewSet(ListNestedModelViewSet):
    serializer_class = ag_serializers.UserSerializer
    permission_classes = (
        P(ag_permissions.IsSuperuser) | P(ag_permissions.is_admin_or_read_only_staff()),)

    model_manager = ag_models.Course.objects
    reverse_to_one_field_name = 'administrators'

    @transaction.atomic()
    def patch(self, request, *args, **kwargs):
        course = self.get_object()
        if 'new_admins' in request.data:
            self.add_admins(course, request.data['new_admins'])
        elif 'remove_admins' in request.data:
            self.remove_admins(course, request.data['remove_admins'])

        return response.Response(status=status.HTTP_204_NO_CONTENT)

    def add_admins(self, course, usernames):
        users_to_add = [
            User.objects.get_or_create(username=username)[0]
            for username in usernames]
        course.administrators.add(*users_to_add)

    def remove_admins(self, course, users_json):
        users_to_remove = User.objects.filter(pk__in=[user['pk'] for user in users_json])

        if self.request.user in users_to_remove:
            raise exceptions.ValidationError(
                {'remove_admins':
                    ["You cannot remove your own admin privileges."]})

        course.administrators.remove(*users_to_remove)
