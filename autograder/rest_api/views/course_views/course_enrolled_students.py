from django.contrib.auth.models import User

from rest_framework import (
    viewsets, mixins, permissions, response, status)

import autograder.core.models as ag_models
import autograder.rest_api.serializers as ag_serializers

from .permissions import IsAdminOrReadOnlyStaff

from ..load_object_mixin import build_load_object_mixin


class CourseEnrolledStudentsViewset(build_load_object_mixin(ag_models.Course),
                                    mixins.ListModelMixin,
                                    viewsets.GenericViewSet):
    serializer_class = ag_serializers.UserSerializer
    permission_classes = (permissions.IsAuthenticated, IsAdminOrReadOnlyStaff)

    def get_queryset(self):
        course = self.load_object(self.kwargs['course_pk'])
        return course.enrolled_students.all()

    def post(self, request, course_pk):
        students_to_add = [
            User.objects.get_or_create(username=username)[0]
            for username in request.data.getlist('new_enrolled_students')
        ]
        self.load_object(course_pk).enrolled_students.add(*students_to_add)
        return response.Response(status=status.HTTP_204_NO_CONTENT)

    def put(self, request, course_pk):
        new_roster = [
            User.objects.get_or_create(username=username)[0]
            for username in request.data.getlist('new_enrolled_students')
        ]
        self.load_object(course_pk).enrolled_students.set(new_roster, clear=True)
        return response.Response(status=status.HTTP_204_NO_CONTENT)

    def delete(self, request, course_pk):
        students_to_remove = [
            User.objects.get_or_create(username=username)[0]
            for username in request.data.getlist('remove_enrolled_students')
        ]
        self.load_object(course_pk).enrolled_students.remove(*students_to_remove)
        return response.Response(status=status.HTTP_204_NO_CONTENT)
