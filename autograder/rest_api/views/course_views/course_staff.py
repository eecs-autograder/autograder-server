from django.contrib.auth.models import User
from django.db import transaction

from rest_framework import (
    viewsets, mixins, permissions, response, status)

import autograder.core.models as ag_models
import autograder.rest_api.serializers as ag_serializers

from .permissions import IsAdminOrReadOnlyStaff

from ..load_object_mixin import build_load_object_mixin


class CourseStaffViewSet(build_load_object_mixin(ag_models.Course, pk_key='course_pk'),
                         mixins.ListModelMixin,
                         viewsets.GenericViewSet):
    serializer_class = ag_serializers.UserSerializer
    permission_classes = (permissions.IsAuthenticated, IsAdminOrReadOnlyStaff)

    def get_queryset(self):
        course = self.get_object()
        return course.staff.all()

    @transaction.atomic()
    def patch(self, request, *args, **kwargs):
        course = self.get_object()
        if 'new_staff' in request.data:
            self.add_staff(course, request.data['new_staff'])
        elif 'remove_staff' in request.data:
            self.remove_staff(course, request.data['remove_staff'])

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
