from django.contrib.auth.models import User

from rest_framework import (
    viewsets, mixins, permissions, response, status)

import autograder.rest_api.serializers as ag_serializers
import autograder.core.models as ag_models

from .permissions import IsAdminOrReadOnlyStaff


class CourseEnrolledStudentsViewset(mixins.ListModelMixin,
                                    viewsets.GenericViewSet):
    serializer_class = ag_serializers.UserSerializer
    permission_classes = (permissions.IsAuthenticated, IsAdminOrReadOnlyStaff)

    def get_object(self, pk):
        course = ag_models.Course.objects.get(pk=pk)
        self.check_object_permissions(self.request, course)
        return course

    def get_queryset(self):
        course = self.get_object(self.kwargs['course_pk'])
        return course.enrolled_students.all()

    def post(self, request, course_pk):
        students_to_add = [
            User.objects.get_or_create(username=username)[0]
            for username in request.data.getlist('new_enrolled_students')
        ]
        self.get_object(course_pk).enrolled_students.add(*students_to_add)
        return response.Response(status=status.HTTP_204_NO_CONTENT)

    def put(self, request, course_pk):
        new_roster = [
            User.objects.get_or_create(username=username)[0]
            for username in request.data.getlist('new_enrolled_students')
        ]
        self.get_object(course_pk).enrolled_students.set(new_roster,
                                                         clear=True)
        return response.Response(status=status.HTTP_204_NO_CONTENT)

    def delete(self, request, course_pk):
        students_to_remove = [
            User.objects.get_or_create(username=username)[0]
            for username in request.data.getlist('remove_enrolled_students')
        ]
        self.get_object(course_pk).enrolled_students.remove(*students_to_remove)
        return response.Response(status=status.HTTP_204_NO_CONTENT)
