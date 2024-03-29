import uuid

from django.db import transaction
from django.shortcuts import get_object_or_404
from django.utils.decorators import method_decorator
from drf_composable_permissions.p import P
from rest_framework import permissions, response, status
from rest_framework.request import Request
from rest_framework.views import APIView

import autograder.core.models as ag_models
import autograder.rest_api.permissions as ag_permissions
from autograder.core.models.copy_project_and_course import copy_course
from autograder.core.models.course import clear_cached_user_roles
from autograder.rest_api.schema import (
    AGListCreateViewSchemaGenerator, AGPatchViewSchemaMixin, AGRetrieveViewSchemaMixin, APITags,
    CustomViewSchema, as_content_obj, as_schema_ref
)
from autograder.rest_api.views.ag_model_views import (
    AGModelAPIView, AGModelDetailView, AlwaysIsAuthenticatedMixin, convert_django_validation_error,
    require_body_params
)


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


class ListCreateCoursePermissions(permissions.BasePermission):
    def has_permission(self, request, view):
        if request.method in permissions.SAFE_METHODS:
            return request.user.is_superuser

        return request.user.is_superuser or request.user.has_perm('core.create_course')


class ListCreateCourseView(APIView):
    schema = AGListCreateViewSchemaGenerator([APITags.courses], ag_models.Course)

    permission_classes = [ListCreateCoursePermissions]

    def get(self, *args, **kwargs):
        return response.Response(
            data=[course.to_dict() for course in ag_models.Course.objects.all()],
            status=status.HTTP_200_OK
        )

    @transaction.atomic
    @convert_django_validation_error
    def post(self, *args, **kwargs):
        new_course = ag_models.Course.objects.validate_and_create(
            **self.request.data
        )
        new_course.admins.add(self.request.user)
        return response.Response(data=new_course.to_dict(), status=status.HTTP_201_CREATED)


class _CourseDetailSchema(AGRetrieveViewSchemaMixin, AGPatchViewSchemaMixin, CustomViewSchema):
    pass


class CourseDetailView(AGModelDetailView):
    schema = _CourseDetailSchema(
        [APITags.courses],
        {'DELETE': {'operation_id': 'pseudoDeleteCourse'}})

    model_manager = ag_models.Course.objects
    permission_classes = [P(ag_permissions.is_admin()) | P(ag_permissions.IsReadOnly)]

    def get(self, *args, **kwargs):
        return self.do_get()

    def patch(self, *args, **kwargs):
        return self.do_patch()

    @transaction.atomic
    def delete(self, *args, **kwargs):
        """
        Pseudo-delete this course by clearing its user rosters  and renaming it.
        """
        course = self.get_object()
        course.name = f'~DELETED_{course.pk}_{course.name}_{uuid.uuid4().hex}'
        course.save()
        course.admins.clear()
        course.staff.clear()
        course.students.clear()
        course.handgraders.clear()
        clear_cached_user_roles(course.pk)

        return response.Response(status=status.HTTP_204_NO_CONTENT)


class CourseUserRolesView(AGModelAPIView):
    schema = CustomViewSchema([APITags.courses, APITags.users], {
        'GET': {
            'operation_id': 'getUserRoles',
            'responses': {
                '200': {
                    'content': {
                        'application/json': {
                            'schema': {'$ref': '#/components/schemas/UserRoles'}
                        }
                    },
                    'description': ''
                }
            }
        }
    })

    model_manager = ag_models.Course.objects

    def get(self, *args, **kwargs):
        course = self.get_object()
        return response.Response(course.get_user_roles(self.request.user))


class CopyCourseView(AGModelAPIView):
    schema = CustomViewSchema([APITags.courses], {
        'POST': {
            'operation_id': 'copyCourse',
            'request': {
                'content': {
                    'application/json': {
                        'schema': {
                            'type': 'object',
                            'required': [
                                'new_name',
                                'new_semester',
                                'new_year',
                            ],
                            'properties': {
                                'new_name': {
                                    'type': 'string'
                                },
                                'new_semester': as_schema_ref(ag_models.Semester),
                                'new_year': {
                                    'type': 'integer'
                                }
                            }
                        }
                    }
                }
            },
            'responses': {
                '201': {
                    'content': as_content_obj(ag_models.Course),
                    'description': ''
                }
            }
        }
    })

    model_manager = ag_models.Course.objects

    permission_classes = [P(ag_permissions.IsSuperuser) | P(ag_permissions.is_admin())]

    @transaction.atomic()
    @convert_django_validation_error
    @method_decorator(require_body_params('new_name', 'new_semester', 'new_year'))
    def post(self, request: Request, *args, **kwargs):
        """
        Makes a copy of the given course and all its projects.
        The projects and all of their  instructor file,
        expected student file, test case, and handgrading data.
        Note that groups, submissions, and results (test case, handgrading,
        etc.) are NOT copied.
        The admin list is copied to the new project, but other permissions
        (staff, students, etc.) are not.
        """
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


class CourseByNameSemesterYearViewSchema(AGRetrieveViewSchemaMixin, CustomViewSchema):
    def _get_operation_id_impl(self, path, method):
        return 'getCourseByFields'


class CourseByNameSemesterYearView(AlwaysIsAuthenticatedMixin, APIView):
    schema = CourseByNameSemesterYearViewSchema(
        tags=[APITags.courses], api_class=ag_models.Course, data={
            'GET': {
                'param_schema_overrides': {
                    'semester': as_schema_ref(ag_models.Semester),
                    'year': {'type': 'integer'}
                }
            }
        })

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
