from django.contrib.auth.models import User

from rest_framework import (
    viewsets, mixins, permissions, response, status)

import autograder.core.models as ag_models
import autograder.rest_api.serializers as ag_serializers

from .permissions import IsAdminOrReadOnlyStaff

from ..load_object_mixin import build_load_object_mixin


class CourseStaffViewSet(build_load_object_mixin(ag_models.Course),
                         mixins.ListModelMixin,
                         viewsets.GenericViewSet):
    serializer_class = ag_serializers.UserSerializer
    permission_classes = (permissions.IsAuthenticated, IsAdminOrReadOnlyStaff)

    def get_queryset(self):
        course = self.load_object(self.kwargs['course_pk'])
        return course.staff.all()

    def post(self, request, course_pk):
        staff_to_add = [
            User.objects.get_or_create(username=username)[0]
            for username in request.data['new_staff']]
        self.load_object(course_pk).staff.add(*staff_to_add)
        return response.Response(status=status.HTTP_204_NO_CONTENT)

    def delete(self, request, course_pk):
        staff_to_remove = [
            User.objects.get_or_create(username=username)[0]
            for username in request.data['remove_staff']]
        self.load_object(course_pk).staff.remove(*staff_to_remove)
        return response.Response(status=status.HTTP_204_NO_CONTENT)
