from django.contrib.auth.models import User
from django.db import transaction

from rest_framework import (
    viewsets, mixins, permissions, response, status)

import autograder.core.models as ag_models
import autograder.rest_api.serializers as ag_serializers

from .permissions import IsAdminOrReadOnlyStaff

from ..load_object_mixin import build_load_object_mixin


class CourseEnrolledStudentsViewset(build_load_object_mixin(ag_models.Course,
                                                            pk_key='course_pk'),
                                    mixins.ListModelMixin,
                                    viewsets.GenericViewSet):
    serializer_class = ag_serializers.UserSerializer
    permission_classes = (permissions.IsAuthenticated, IsAdminOrReadOnlyStaff)

    def get_queryset(self):
        course = self.get_object()
        return course.enrolled_students.all()

    @transaction.atomic()
    def patch(self, request, *args, **kwargs):
        course = self.get_object()
        if 'new_enrolled_students' in request.data:
            self.add_enrolled_students(
                course, request.data['new_enrolled_students'])
        elif 'remove_enrolled_students' in request.data:
            self.remove_enrolled_students(
                course, request.data['remove_enrolled_students'])

        return response.Response(status=status.HTTP_204_NO_CONTENT)

    def add_enrolled_students(self, course, usernames):
        students_to_add = [
            User.objects.get_or_create(username=username)[0]
            for username in usernames]
        self.get_object().enrolled_students.add(*students_to_add)

    def remove_enrolled_students(self, course, users_json):
        students_to_remove = User.objects.filter(
            pk__in=[user['pk'] for user in users_json])
        self.get_object().enrolled_students.remove(*students_to_remove)

    @transaction.atomic()
    def put(self, request, course_pk):
        new_roster = [
            User.objects.get_or_create(username=username)[0]
            for username in request.data['new_enrolled_students']
        ]
        self.load_object(course_pk).enrolled_students.set(new_roster, clear=True)
        return response.Response(status=status.HTTP_204_NO_CONTENT)
