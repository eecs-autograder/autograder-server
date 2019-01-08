from django.db import transaction
from django.shortcuts import get_object_or_404
from django.utils.decorators import method_decorator
from drf_composable_permissions.p import P
from drf_yasg.openapi import Parameter, Schema
from drf_yasg.utils import swagger_auto_schema
from rest_framework import mixins, permissions, decorators, response, status
from rest_framework.permissions import DjangoModelPermissions, BasePermission
from rest_framework.request import Request
from rest_framework.views import APIView

import autograder.core.models as ag_models
import autograder.rest_api.permissions as ag_permissions
import autograder.rest_api.serializers as ag_serializers
from autograder.core.models.copy_project_and_course import copy_course
from autograder.rest_api import transaction_mixins
from autograder.rest_api.views.ag_model_views import (
    AGModelGenericViewSet, AlwaysIsAuthenticatedMixin, require_body_params,
    convert_django_validation_error)
from autograder.rest_api.views.schema_generation import APITags, AGModelViewAutoSchema


class CoursePermissions(permissions.BasePermission):
    def has_permission(self, request: Request, view):
        if view.action == 'list':
            return request.user.is_superuser
        if view.action == 'create':
            return request.user.is_superuser or request.user.has_perm('core.create_course')

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

    def perform_create(self, serializer):
        course = serializer.save()
        course.admins.add(self.request.user)

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


class CanCreateCourses(BasePermission):
    def has_permission(self, request, view):
        return request.user.has_perm('core.create_course')

    def has_object_permission(self, request, view, obj):
        return self.has_permission(request, view)


class CopyCourseView(AGModelGenericViewSet):
    api_tags = [APITags.courses]

    pk_key = 'course_pk'
    model_manager = ag_models.Course.objects

    serializer_class = ag_serializers.CourseSerializer

    permission_classes = P(ag_permissions.IsSuperuser) | P(ag_permissions.is_admin()),

    @swagger_auto_schema(
        operation_description="""Makes a copy of the given course and all its projects.
            The projects and all of their  instructor file,
            expected student file, test case, and handgrading data.
            Note that groups, submissions, and results (test case, handgrading,
            etc.) are NOT copied.
            The admin list is copied to the new project, but other permissions
            (staff, students, etc.) are not.
        """,
        request_body_parameters=[
            Parameter('new_name', in_='body', type='string', required=True),
            Parameter(
                'new_semester', in_='body', type='string', required=True,
                description='Must be one of: '
                            + f'{", ".join((semester.value for semester in ag_models.Semester))}'),
            Parameter('new_year', in_='body', type='integer', required=True)
        ],
    )
    @transaction.atomic()
    @convert_django_validation_error
    @method_decorator(require_body_params('new_name', 'new_semester', 'new_year'))
    def copy_course(self, request: Request, *args, **kwargs):
        course: ag_models.Course = self.get_object()

        new_semester = request.data['new_semester']
        try:
            new_semester = ag_models.Semester(new_semester)
        except ValueError:
            return response.Response(status=status.HTTP_400_BAD_REQUEST,
                                     data=f'"{new_semester}" is not a valid semester.')

        new_course = copy_course(
            course=course,
            new_course_name=request.data['new_name'],
            new_course_semester=new_semester,
            new_course_year=request.data['new_year'])

        return response.Response(status=status.HTTP_201_CREATED, data=new_course.to_dict())

    @classmethod
    def as_view(cls, actions=None, **initkwargs):
        return super().as_view(actions={'post': 'copy_course'}, **initkwargs)


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
