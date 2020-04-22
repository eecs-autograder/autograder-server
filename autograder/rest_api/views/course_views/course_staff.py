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


class CourseStaffViewSet(NestedModelView):
    schema = CustomViewSchema([APITags.rosters], {
        'GET': {
            'operation_id': 'listCourseStaff',
            'responses': {
                '200': {
                    'content': as_array_content_obj(User)
                }
            }
        },
        'POST': {
            'operation_id': 'addCourseStaff',
            'request': {
                'content': {
                    'application/json': {
                        'schema': {
                            'type': 'object',
                            'required': ['new_staff'],
                            'properties': {
                                'new_staff': {
                                    'type': 'array',
                                    'items': {'type': 'string', 'format': 'username'},
                                    'description': (
                                        'Usernames to be granted staff privileges for the course.'
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
            'operation_id': 'removeCourseStaff',
            'request': {
                'content': {
                    'application/json': {
                        'schema': {
                            'type': 'object',
                            'required': ['remove_staff'],
                            'properties': {
                                'remove_staff': {
                                    'type': 'array',
                                    'items': as_schema_ref(User),
                                    'description': (
                                        'Users whose staff privileges should be '
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

    permission_classes = [ag_permissions.is_admin_or_read_only_staff_or_handgrader()]

    model_manager = ag_models.Course.objects
    nested_field_name = 'staff'

    def get(self, *args, **kwargs):
        return self.do_list()

    def serialize_object(self, obj):
        return serialize_user(obj)

    @transaction.atomic()
    @method_decorator(require_body_params('new_staff'))
    def post(self, request, *args, **kwargs):
        course = self.get_object()
        self.add_staff(course, request.data['new_staff'])

        clear_cached_user_roles(course.pk)
        return response.Response(status=status.HTTP_204_NO_CONTENT)

    @transaction.atomic()
    @method_decorator(require_body_params('remove_staff'))
    def patch(self, request, *args, **kwargs):
        course = self.get_object()
        self.remove_staff(course, request.data['remove_staff'])

        clear_cached_user_roles(course.pk)
        return response.Response(status=status.HTTP_204_NO_CONTENT)

    def add_staff(self, course, usernames):
        staff_to_add = [
            User.objects.get_or_create(username=username)[0]
            for username in usernames]
        course.staff.add(*staff_to_add)

    def remove_staff(self, course, users_json):
        staff_to_remove = User.objects.filter(
            pk__in=[user['pk'] for user in users_json])
        course.staff.remove(*staff_to_remove)
