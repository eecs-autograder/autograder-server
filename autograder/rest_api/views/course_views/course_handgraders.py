from django.contrib.auth.models import User
from django.db import transaction
from django.utils.decorators import method_decorator
from rest_framework import response, status

import autograder.core.models as ag_models
import autograder.rest_api.permissions as ag_permissions
from autograder.core.models.course import clear_cached_user_roles
from autograder.rest_api.schema import (APITags, CustomViewSchema, as_array_content_obj,
                                        as_schema_ref)
from autograder.rest_api.serialize_user import serialize_user
from autograder.rest_api.views.ag_model_views import NestedModelView, require_body_params


class CourseHandgradersViewSet(NestedModelView):
    schema = CustomViewSchema([APITags.rosters], {
        'GET': {
            'operation_id': 'listCourseHandgraders',
            'responses': {
                '200': {
                    'content': as_array_content_obj(User),
                    'description': ''
                }
            }
        },
        'POST': {
            'operation_id': 'addCourseHandgraders',
            'request': {
                'content': {
                    'application/json': {
                        'schema': {
                            'type': 'object',
                            'required': ['new_handgraders'],
                            'properties': {
                                'new_handgraders': {
                                    'type': 'array',
                                    'items': {'type': 'string', 'format': 'username'},
                                    'description': (
                                        'Usernames to be granted handgrading '
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
            'operation_id': 'removeCourseHandgraders',
            'request': {
                'content': {
                    'application/json': {
                        'schema': {
                            'type': 'object',
                            'required': ['remove_handgraders'],
                            'properties': {
                                'remove_handgraders': {
                                    'type': 'array',
                                    'items': as_schema_ref(User),
                                    'description': (
                                        'Users to revoke handgrading privileges from.'
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
    nested_field_name = 'handgraders'

    def get(self, *args, **kwargs):
        return self.do_list()

    def serialize_object(self, obj):
        return serialize_user(obj)

    @transaction.atomic()
    @method_decorator(require_body_params('new_handgraders'))
    def post(self, request, *args, **kwargs):
        course = self.get_object()
        self.add_handgraders(course, request.data['new_handgraders'])

        clear_cached_user_roles(course.pk)
        return response.Response(status=status.HTTP_204_NO_CONTENT)

    @transaction.atomic()
    @method_decorator(require_body_params('remove_handgraders'))
    def patch(self, request, *args, **kwargs):
        course = self.get_object()
        self.remove_handgraders(course, request.data['remove_handgraders'])

        clear_cached_user_roles(course.pk)
        return response.Response(status=status.HTTP_204_NO_CONTENT)

    def add_handgraders(self, course: ag_models.Course, usernames):
        handgraders_to_add = [
            User.objects.get_or_create(username=username)[0]
            for username in usernames]
        course.handgraders.add(*handgraders_to_add)

    def remove_handgraders(self, course: ag_models.Course, users_json):
        handgraders_to_remove = User.objects.filter(
            pk__in=[user['pk'] for user in users_json])
        course.handgraders.remove(*handgraders_to_remove)
