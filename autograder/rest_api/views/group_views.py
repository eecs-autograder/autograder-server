import itertools
import os
import shutil
import tempfile

from django.contrib.auth.models import User
from django.db import transaction
from django.db.models import Prefetch
from django.utils import timezone
from django.utils.decorators import method_decorator
from drf_composable_permissions.p import P
from rest_framework import decorators, mixins, permissions, response, status

import autograder.core.models as ag_models
import autograder.core.utils as core_ut
import autograder.rest_api.serializers as ag_serializers
import autograder.utils.testing as test_ut
from autograder import utils
from autograder.core.models.get_ultimate_submissions import get_ultimate_submission
from autograder.rest_api import permissions as ag_permissions
from autograder.rest_api import transaction_mixins
from autograder.rest_api.schema import (AGListViewSchemaMixin, AGRetrieveViewSchemaMixin, APITags,
                                        CustomViewSchema, RequestBody, as_content_obj)
from autograder.rest_api.views.ag_model_views import (AGModelAPIView, AGModelDetailView,
                                                      NestedModelView,
                                                      convert_django_validation_error,
                                                      require_body_params, require_query_params)

_MEMBER_NAMES_REQUEST_BODY: RequestBody = {
    'content': {
        'application/json': {
            'schema': {
                'type': 'object',
                'properties': {
                    'member_names': {
                        'type': 'array',
                        'items': {
                            'type': 'string',
                            'format': 'username'
                        }
                    }
                }
            }
        }
    }
}


class _ListCreateGroupSchema(AGListViewSchemaMixin, CustomViewSchema):
    pass


class ListCreateGroupsView(NestedModelView):
    schema = _ListCreateGroupSchema([APITags.groups], api_class=ag_models.Group, data={
        'POST': {
            'request': _MEMBER_NAMES_REQUEST_BODY,
            'responses': {
                '201': {
                    'content': as_content_obj(ag_models.Group)
                }
            }
        }
    })

    permission_classes = [
        P(ag_permissions.is_admin())
        | ((P(ag_permissions.is_staff()) | P(ag_permissions.is_handgrader()))
            & ag_permissions.IsReadOnly)
    ]

    pk_key = 'project_pk'
    model_manager = ag_models.Project.objects.select_related('course')
    nested_field_name = 'groups'
    parent_obj_field_name = 'project'

    def get_queryset(self):
        queryset = super().get_queryset()
        if self.request.method.lower() == 'get':
            queryset = queryset.prefetch_related(
                Prefetch('submissions',
                         ag_models.Submission.objects.defer('denormalized_ag_test_results'))
            )

        return queryset

    def get(self, *args, **kwargs):
        return self.do_list()

    @convert_django_validation_error
    @transaction.atomic()
    @method_decorator(require_body_params('member_names'))
    def post(self, request, *args, **kwargs):
        """
        Create a new group with the specified members.
        Size restrictions are ignored.
        Available to admins only.
        """
        project = self.get_object()

        users = [
            User.objects.get_or_create(username=username)[0]
            for username in request.data.pop('member_names')]

        utils.lock_users(users)
        # Keep this hook immediately after locking the users.
        test_ut.mocking_hook()

        group = ag_models.Group.objects.validate_and_create(
            members=users,
            project=project,
            check_group_size_limits=not project.course.is_admin(request.user)
        )
        return response.Response(group.to_dict(), status.HTTP_201_CREATED)


class _CanCreateSoloGroup(permissions.BasePermission):
    def has_object_permission(self, request, view, project):
        if project.course.is_staff(request.user):
            return True

        if not project.visible_to_students:
            return False

        return (project.course.is_student(request.user) or project.guests_can_submit)


class CreateSoloGroupView(AGModelAPIView):
    schema = CustomViewSchema([APITags.groups], {
        'POST': {
            'responses': {
                '201': {
                    'content': as_content_obj(ag_models.Group)
                }
            }
        }
    })

    permission_classes = [_CanCreateSoloGroup]

    pk_key = 'project_pk'
    model_manager = ag_models.Project.objects.select_related('course')

    api_tags = [APITags.groups]

    @convert_django_validation_error
    @transaction.atomic()
    def post(self, request, *args, **kwargs):
        """
        Creates a group containing only the user making the request.
        """
        project = self.get_object()

        utils.lock_users([request.user])

        group = ag_models.Group.objects.validate_and_create(
            members=[request.user],
            project=project,
            check_group_size_limits=not project.course.is_staff(request.user)
        )
        return response.Response(group.to_dict(), status.HTTP_201_CREATED)


is_staff_or_member = ag_permissions.is_staff_or_group_member()
can_view_project = ag_permissions.can_view_project(lambda group: group.project)
group_permissions = (P(ag_permissions.is_admin())
                     | (P(ag_permissions.IsReadOnly) & can_view_project & is_staff_or_member))


class _UltimateSubmissionPermissions(permissions.BasePermission):
    def has_object_permission(self, request, view, group):
        project = group.project
        course = group.project.course
        is_staff = course.is_staff(request.user)

        # Staff and higher can always view their own ultimate submission
        if is_staff and group.members.filter(pk=request.user.pk).exists():
            return True

        return (ag_permissions.deadline_is_past(group, request.user)
                and not project.hide_ultimate_submission_fdbk)


class _GroupDetailSchema(AGRetrieveViewSchemaMixin, CustomViewSchema):
    pass


class GroupDetailView(AGModelDetailView):
    schema = _GroupDetailSchema([APITags.groups], {
        'PATCH': {
            'request': _MEMBER_NAMES_REQUEST_BODY,
            'responses': {
                '200': {
                    'content': as_content_obj(ag_models.Group)
                }
            }
        }
    })

    permission_classes = [group_permissions]

    model_manager = ag_models.Group.objects.select_related(
        'project__course').prefetch_related('members', 'submissions')

    def get(self, *args, **kwargs):
        return self.do_get()

    @convert_django_validation_error
    @transaction.atomic()
    def patch(self, request, *args, **kwargs):
        group = self.get_object()

        update_data = dict(request.data)
        if 'member_names' in update_data:
            users = [
                User.objects.get_or_create(
                    username=username)[0]
                for username in update_data.pop('member_names')]

            utils.lock_users(users)
            # Keep this hook just after the users are locked
            test_ut.mocking_hook()

            update_data['members'] = users
            update_data['check_group_size_limits'] = False
            update_data['ignore_guest_restrictions'] = False

        group.validate_and_update(**update_data)
        return response.Response(group.to_dict())

    @transaction.atomic
    def delete(self, request, *args, **kwargs):
        """
        "Deletes" a group by removing all of its members. Each group
        member is replaced with a dummy user whose username contains
        the group's pk and the original username. This allows "deleted"
        groups to be easily viewable and recoverable by the user.
        """
        group = self.get_object()
        new_members = []
        for username in group.member_names:
            new_username = f'~deleted_{group.pk}_{username}'
            new_members.append(User.objects.get_or_create(username=new_username)[0])

        group.validate_and_update(
            members=new_members, check_group_size_limits=False, ignore_guest_restrictions=True)

        return response.Response(status=status.HTTP_204_NO_CONTENT)


class GroupUltimateSubmissionView(AGModelAPIView):
    schema = CustomViewSchema([APITags.groups, APITags.submissions], {
        'GET': {
            'responses': {
                '200': {
                    'content': as_content_obj(ag_models.Submission)
                }
            }
        }
    })

    model_manager = model_manager = ag_models.Group.objects.select_related('project__course')
    permission_classes = [group_permissions, _UltimateSubmissionPermissions]

    def get(self, request, *args, **kwargs):
        """
        Permissions details:
        - The normal group and submission viewing permissions apply
          first.
        - Staff members can always view their own ultimate submission.
        - Staff members can only view student and other staff ultimate
          submissions if the project closing time has passed.
        - If the project closing time has passed, staff can view student
          and other staff ultimate submissions regardless of whether
          ultimate submissions are marked as hidden.
        - Students can view their ultimate submissions as long as the
          closing time has passed and ultimate submissions are not
          overridden as being hidden.
        """
        group = self.get_object()
        ultimate_submission = get_ultimate_submission(group, user=request.user)
        if ultimate_submission is None:
            return response.Response(status=status.HTTP_404_NOT_FOUND)

        return response.Response(ultimate_submission.to_dict())


class MergeGroupsView(AGModelAPIView):
    schema = CustomViewSchema([APITags.groups], {
        'POST': {
            'responses': {
                '201': {
                    'content': as_content_obj(ag_models.Group)
                }
            }
        }
    })

    permission_classes = [ag_permissions.is_admin()]
    model_manager = ag_models.Group.objects

    @convert_django_validation_error
    @transaction.atomic()
    def post(self, request, *args, **kwargs):
        """
        Merge two groups together, preserving their submissions, and
        return the newly created group.
        """
        other_group_pk = kwargs['other_group_pk']

        group1 = self.get_object()
        group2 = self.get_object(pk_override=other_group_pk)

        if group1.project != group2.project:
            return response.Response(
                data={'groups': 'Cannot merge groups from different projects'},
                status=status.HTTP_400_BAD_REQUEST
            )

        merged_members = list(group1.members.all()) + list(group2.members.all())
        project = group1.project

        # Can't have duplicate members between groups in a project,
        # but still need to copy submissions before they get
        # cascade-deleted
        group1.members.clear()
        group2.members.clear()

        merged_group = ag_models.Group.objects.validate_and_create(
            merged_members,
            check_group_size_limits=False,
            project=project,
            extended_due_date=self._get_merged_extended_due_date(group1, group2),
            late_days_used={
                **group1.late_days_used,
                **group2.late_days_used,
            },
        )
        # Group.save() sets bonus_submissions_remaining on create, so
        # we overwrite that value here.
        merged_group.bonus_submissions_remaining = min(
            group1.bonus_submissions_remaining, group2.bonus_submissions_remaining)
        merged_group.save()

        self._merge_group_files(group1=group1, group2=group2, merged_group=merged_group)

        group1.delete()
        group2.delete()

        return response.Response(merged_group.to_dict(), status=status.HTTP_201_CREATED)

    def _merge_group_files(self, group1, group2, merged_group):
        tempdir_path = tempfile.mkdtemp()

        for submission in itertools.chain(group1.submissions.all(),
                                          group2.submissions.all()):
            shutil.copytree(
                core_ut.get_submission_dir(submission),
                os.path.join(tempdir_path,
                             core_ut.get_submission_dir_basename(submission)))

            submission.group = merged_group
            submission.save()

        merged_group_dir = core_ut.get_student_group_dir(merged_group)
        shutil.rmtree(merged_group_dir)
        shutil.move(tempdir_path, merged_group_dir)

    def _get_merged_extended_due_date(self, group1, group2):
        if group1.extended_due_date is None:
            return group2.extended_due_date
        if group2.extended_due_date is None:
            return group1.extended_due_date

        return max(group1.extended_due_date, group2.extended_due_date)
