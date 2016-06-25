from django.contrib.auth.models import User

from rest_framework import (
    viewsets, mixins, permissions, response, status)

import autograder.rest_api.serializers as ag_serializers

from .nested_course_view_mixin import NestedCourseViewMixin
from .permissions import IsAdminOrReadOnlyStaff


class CourseEnrolledStudentsViewset(NestedCourseViewMixin,
                                    mixins.ListModelMixin,
                                    viewsets.GenericViewSet):
    serializer_class = ag_serializers.UserSerializer
    permission_classes = (permissions.IsAuthenticated, IsAdminOrReadOnlyStaff)

    def get_queryset(self):
        course = self.load_course()
        return course.enrolled_students.all()

    def post(self, request, course_pk):
        students_to_add = [
            User.objects.get_or_create(username=username)[0]
            for username in request.data.getlist('new_enrolled_students')
        ]
        self.load_course().enrolled_students.add(*students_to_add)
        return response.Response(status=status.HTTP_204_NO_CONTENT)

    def put(self, request, course_pk):
        new_roster = [
            User.objects.get_or_create(username=username)[0]
            for username in request.data.getlist('new_enrolled_students')
        ]
        self.load_course().enrolled_students.set(new_roster, clear=True)
        return response.Response(status=status.HTTP_204_NO_CONTENT)

    def delete(self, request, course_pk):
        students_to_remove = [
            User.objects.get_or_create(username=username)[0]
            for username in request.data.getlist('remove_enrolled_students')
        ]
        self.load_course().enrolled_students.remove(*students_to_remove)
        return response.Response(status=status.HTTP_204_NO_CONTENT)
