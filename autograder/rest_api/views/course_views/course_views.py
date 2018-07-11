from django.shortcuts import get_object_or_404
from django.utils.decorators import method_decorator
from drf_yasg.openapi import Parameter, Schema
from drf_yasg.utils import swagger_auto_schema
from rest_framework import mixins, permissions, decorators, response, status
from rest_framework.request import Request
from rest_framework.views import APIView

import autograder.core.models as ag_models
import autograder.rest_api.serializers as ag_serializers
from autograder.rest_api import transaction_mixins
from autograder.rest_api.views.ag_model_views import AGModelGenericViewSet, \
    AlwaysIsAuthenticatedMixin, require_query_params
from autograder.rest_api.views.schema_generation import APITags, AGModelViewAutoSchema


class CoursePermissions(permissions.BasePermission):
    def has_permission(self, request, view):
        if view.action in ['list', 'create']:
            return request.user.is_superuser

        return True

    def has_object_permission(self, request, view, course):
        if view.action == 'retrieve' or request.method.lower() == 'get':
            return True

        return course.is_admin(request.user)


_my_roles_schema = Schema(
    type='object',
    properties={
        'is_admin': Parameter('is_admin', 'body', type='boolean'),
        'is_staff': Parameter('is_staff', 'body', type='boolean'),
        'is_student': Parameter('is_student', 'body', type='boolean'),
        'is_handgrader': Parameter('is_handgrader', 'body', type='boolean'),
    }
)


class CourseViewSet(mixins.ListModelMixin,
                    mixins.RetrieveModelMixin,
                    transaction_mixins.TransactionPartialUpdateMixin,
                    transaction_mixins.TransactionCreateMixin,
                    AGModelGenericViewSet):
    serializer_class = ag_serializers.CourseSerializer
    permission_classes = (permissions.IsAuthenticated, CoursePermissions,)

    model_manager = ag_models.Course.objects

    api_tags = [APITags.courses]

    def get_queryset(self):
        return ag_models.Course.objects.all()

    @swagger_auto_schema(responses={'200': _my_roles_schema}, api_tags=[APITags.permissions])
    @decorators.detail_route()
    def my_roles(self, request, *args, **kwargs):
        course = self.get_object()
        return response.Response({
            'is_admin': course.is_admin(request.user),
            'is_staff': course.is_staff(request.user),
            'is_student': course.is_student(request.user),
            'is_handgrader': course.is_handgrader(request.user)
        })


class CourseByNameSemesterYearView(AlwaysIsAuthenticatedMixin, APIView):
    swagger_schema = AGModelViewAutoSchema
    api_tags = [APITags.courses]

    @swagger_auto_schema(
        request_body_parameters=[
            Parameter('name', in_='path', type='string', required=True),
            Parameter(
                'semester', in_='path', type='string', required=True,
                description='Must be one of: '
                            + f'{", ".join((semester.value for semester in ag_models.Semester))}'),
            Parameter('year', in_='path', type='integer', required=True)
        ]
    )
    def get(self, request: Request, *args, **kwargs):
        name = kwargs.get('name')
        semester = kwargs.get('semester')
        try:
            semester = ag_models.Semester(semester)
        except ValueError:
            return response.Response(
                status=status.HTTP_400_BAD_REQUEST, data=f'Invalid semester: {semester}')
        year = kwargs.get('year')

        course = get_object_or_404(
            ag_models.Course.objects, name=name, semester=semester, year=year)

        return response.Response(course.to_dict())
