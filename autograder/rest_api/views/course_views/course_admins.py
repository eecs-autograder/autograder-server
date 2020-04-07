from django.contrib.auth.models import User
from django.db import transaction
from django.utils.decorators import method_decorator
from drf_composable_permissions.p import P
from rest_framework import exceptions, response, status

import autograder.core.models as ag_models
import autograder.rest_api.permissions as ag_permissions
import autograder.rest_api.serializers as ag_serializers
from autograder.core.models.course import clear_cached_user_roles
from autograder.rest_api.schema import (AGRetrieveViewSchemaMixin, APITags,
                                        CustomViewSchema)
from autograder.rest_api.views.ag_model_views import (NestedModelView,
                                                      require_body_params)


class _Schema(AGRetrieveViewSchemaMixin, CustomViewSchema):
    pass


class CourseAdminViewSet(NestedModelView):
    schema = _Schema(tags=[APITags.rosters], api_class=User, data={
        'POST': {
            'request_payload': {
                'body': {
                    'type': 'object',
                    'required': ['new_admins'],
                    'properties': {
                        'new_admins': {
                            'type': 'array',
                            'items': {'type': 'string', 'format': 'username'},
                            'description': (
                                'Usernames who should be granted admin privileges for the course.'
                            )
                        }
                    }
                }
            },
            'responses': {'204': None}
        },
        'PATCH': {
            'request_payload': {
                'body': {
                    'type': 'object',
                    'required': ['remove_admins'],
                    'properties': {
                        'remove_admins': {
                            'type': 'array',
                            'items': {
                                '$ref': '#/components/schemas/User'
                            },
                            'description': (
                                'Users whose admin privileges should be revoked for the course.'
                            )
                        }
                    }
                }
            },
            'responses': {'204': None}
        }
    })

    permission_classes = [
        P(ag_permissions.IsSuperuser)
        | P(ag_permissions.is_admin_or_read_only_staff_or_handgrader())
    ]

    model_manager = ag_models.Course.objects
    nested_field_name = 'admins'

    def get(self, *args, **kwargs):
        return self.do_list()

    @transaction.atomic()
    @method_decorator(require_body_params('new_admins'))
    def post(self, request, *args, **kwargs):
        course = self.get_object()
        self.add_admins(course, request.data['new_admins'])

        clear_cached_user_roles(course.pk)
        return response.Response(status=status.HTTP_204_NO_CONTENT)

    @transaction.atomic()
    @method_decorator(require_body_params('remove_admins'))
    def patch(self, request, *args, **kwargs):
        course = self.get_object()
        self.remove_admins(course, request.data['remove_admins'])

        clear_cached_user_roles(course.pk)
        return response.Response(status=status.HTTP_204_NO_CONTENT)

    def add_admins(self, course: ag_models.Course, usernames):
        users_to_add = [
            User.objects.get_or_create(username=username)[0]
            for username in usernames]
        course.admins.add(*users_to_add)

    def remove_admins(self, course: ag_models.Course, users_json):
        users_to_remove = User.objects.filter(pk__in=[user['pk'] for user in users_json])

        if self.request.user in users_to_remove:
            raise exceptions.ValidationError(
                {'remove_admins': ["You cannot remove your own admin privileges."]})

        course.admins.remove(*users_to_remove)
