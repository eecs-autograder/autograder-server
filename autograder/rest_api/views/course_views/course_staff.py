from django.contrib.auth.models import User

from rest_framework import (
    viewsets, mixins, permissions, response, status)

import autograder.rest_api.serializers as ag_serializers

from .nested_course_view_mixin import NestedCourseViewMixin
from .permissions import IsAdminOrReadOnlyStaff


class CourseStaffViewSet(NestedCourseViewMixin,
                         mixins.ListModelMixin,
                         viewsets.GenericViewSet):
    serializer_class = ag_serializers.UserSerializer
    permission_classes = (permissions.IsAuthenticated, IsAdminOrReadOnlyStaff)

    def get_queryset(self):
        course = self.load_course()
        return course.staff.all()

    def post(self, request, course_pk):
        staff_to_add = [
            User.objects.get_or_create(username=username)[0]
            for username in request.data.getlist('new_staff')]
        self.load_course().staff.add(*staff_to_add)
        return response.Response(status=status.HTTP_204_NO_CONTENT)

    def delete(self, request, course_pk):
        staff_to_remove = [
            User.objects.get_or_create(username=username)[0]
            for username in request.data.getlist('remove_staff')]
        self.load_course().staff.remove(*staff_to_remove)
        return response.Response(status=status.HTTP_204_NO_CONTENT)
