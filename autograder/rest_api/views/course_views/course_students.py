from django.contrib.auth.models import User
from django.db import transaction
from django.utils.decorators import method_decorator
from rest_framework import response, status

import autograder.core.models as ag_models
import autograder.rest_api.permissions as ag_permissions
from autograder.core.models.course import clear_cached_user_roles
from autograder.rest_api.schema import (AGRetrieveViewSchemaMixin, APITags, CustomViewSchema,
                                        as_schema_ref)
from autograder.rest_api.serialize_user import serialize_user
from autograder.rest_api.views.ag_model_views import NestedModelView, require_body_params


class _Schema(AGRetrieveViewSchemaMixin, CustomViewSchema):
    pass


class CourseStudentsViewSet(NestedModelView):
    schema = _Schema(tags=[APITags.rosters], api_class=User, data={
        'POST': {
            'request': {
                'content': {
                    'application/json': {
                        'schema': {
                            'type': 'object',
                            'required': ['new_students'],
                            'properties': {
                                'new_students': {
                                    'type': 'array',
                                    'items': {'type': 'string', 'format': 'username'},
                                    'description': (
                                        'Usernames to be granted student '
                                        'privileges for the course.'
                                    )
                                }
                            }
                        }
                    }
                }
            },
            'responses': {'204': None}
        },
        'PUT': {
            'request': {
                'content': {
                    'application/json': {
                        'schema': {
                            'type': 'object',
                            'required': ['new_students'],
                            'properties': {
                                'new_students': {
                                    'type': 'array',
                                    'items': {'type': 'string', 'format': 'username'},
                                    'description': (
                                        'Usernames to be granted student '
                                        'privileges for the course.'
                                    )
                                }
                            }
                        }
                    }
                }
            },
            'responses': {'204': None}
        },
        'PATCH': {
            'request': {
                'content': {
                    'application/json': {
                        'schema': {
                            'type': 'object',
                            'required': ['remove_students'],
                            'properties': {
                                'remove_students': {
                                    'type': 'array',
                                    'items': {
                                        '$ref': as_schema_ref(User)
                                    },
                                    'description': (
                                        'Users whose student privileges should be '
                                        'revoked for the course.'
                                    )
                                }
                            }
                        }
                    }
                }
            },
            'responses': {'204': None}
        }
    })

    permission_classes = [ag_permissions.is_admin_or_read_only_staff()]

    model_manager = ag_models.Course.objects
    nested_field_name = 'students'

    def get(self, *args, **kwargs):
        return self.do_list()

    def serialize_object(self, obj):
        return serialize_user(obj)

    @transaction.atomic()
    @method_decorator(require_body_params('new_students'))
    def post(self, request, *args, **kwargs):
        course = self.get_object()
        self.add_students(course, request.data['new_students'])

        clear_cached_user_roles(course.pk)
        return response.Response(status=status.HTTP_204_NO_CONTENT)

    @transaction.atomic()
    @method_decorator(require_body_params('new_students'))
    def put(self, request, *args, **kwargs):
        """
        Completely REPLACES the student roster with the usernames
        included in the request.
        """
        new_roster = [
            User.objects.get_or_create(username=username)[0]
            for username in request.data['new_students']
        ]
        course = self.get_object()
        course.students.set(new_roster, clear=True)

        clear_cached_user_roles(course.pk)
        return response.Response(status=status.HTTP_204_NO_CONTENT)

    @transaction.atomic()
    @method_decorator(require_body_params('remove_students'))
    def patch(self, request, *args, **kwargs):
        course = self.get_object()
        self.remove_students(course, request.data['remove_students'])

        clear_cached_user_roles(course.pk)
        return response.Response(status=status.HTTP_204_NO_CONTENT)

    def add_students(self, course: ag_models.Course, usernames):
        students_to_add = [
            User.objects.get_or_create(username=username)[0]
            for username in usernames]
        course.students.add(*students_to_add)

    def remove_students(self, course: ag_models.Course, users_json):
        students_to_remove = User.objects.filter(
            pk__in=[user['pk'] for user in users_json])
        course.students.remove(*students_to_remove)
