from django.core.exceptions import ObjectDoesNotExist
from django.db import transaction
from django.http.response import FileResponse
from django.utils import timezone
from django.utils.decorators import method_decorator
from drf_composable_permissions.p import P
from drf_yasg.openapi import Parameter
from drf_yasg.utils import swagger_auto_schema
from rest_framework import decorators, exceptions, mixins, response, status

import autograder.core.models as ag_models
import autograder.rest_api.permissions as ag_permissions
import autograder.rest_api.serializers as ag_serializers
import autograder.utils.testing as test_ut
from autograder.rest_api import transaction_mixins
from autograder.rest_api.views.ag_model_views import (AGModelGenericViewSet,
                                                      ListCreateNestedModelViewSet,
                                                      require_body_params, require_query_params,
                                                      ListNestedModelViewSet)

can_view_group = (
    P(ag_permissions.IsReadOnly)
    & P(ag_permissions.can_view_project())
    & P(ag_permissions.is_staff_or_group_member())
)


can_submit = (
    ~P(ag_permissions.IsReadOnly)
    & P(ag_permissions.can_view_project())
    & P(ag_permissions.is_group_member())
)


list_create_submission_permissions = can_view_group | can_submit


class ListCreateSubmissionViewSet(ListCreateNestedModelViewSet):
    serializer_class = ag_serializers.SubmissionSerializer
    permission_classes = (list_create_submission_permissions,)

    model_manager = ag_models.Group.objects

    to_one_field_name = 'group'
    reverse_to_one_field_name = 'submissions'

    @swagger_auto_schema(
        request_body_parameters=[
            Parameter(name='submitted_files', in_='body',
                      description='The files being submitted, as multipart/form-data.',
                      type='List[file]')
        ]
    )
    @transaction.atomic()
    def create(self, request, *args, **kwargs):
        # NOTE: The way that submitted_files gets encoded in requests,
        # sending no files (which is valid) will cause the key 'submitted_files'
        # to not show up in the request body. Therefore, we will NOT require
        # the presence of a 'submitted_files' key in the request.
        for key in request.data:
            if key != 'submitted_files':
                raise exceptions.ValidationError({'invalid_fields': [key]})

        timestamp = timezone.now()
        group: ag_models.Group = self.get_object()
        # Keep this mocking hook just after we call get_object()
        test_ut.mocking_hook()

        self._validate_can_submit(request, group, timestamp)
        return super().create(request, *args, **kwargs)

    def perform_create(self, serializer):
        serializer.is_valid()
        serializer.save(group=self.get_object(),
                        submitter=self.request.user.username)

    def _validate_can_submit(self, request, group: ag_models.Group, timestamp):
        has_active_submission = group.submissions.filter(
            status__in=ag_models.Submission.GradingStatus.active_statuses
        ).exists()
        if has_active_submission:
            raise exceptions.ValidationError(
                {'submission': 'Unable to resubmit while current submission is being processed'})

        # Provided they don't have a submission being processed, staff
        # should always be able to submit.
        if (group.project.course.is_staff(request.user)
                and group.members.filter(pk=request.user.pk).exists()):
            return

        if group.project.disallow_student_submissions:
            raise exceptions.ValidationError(
                {'submission': 'Submitting has been temporarily disabled for this project'})

        closing_time = group.extended_due_date
        if closing_time is None:
            closing_time = group.project.closing_time
        deadline_past = closing_time is not None and timestamp > closing_time

        if deadline_past:
            raise exceptions.ValidationError(
                {'submission': 'The closing time for this project has passed'})

        has_hard_daily_limit = (group.project.submission_limit_per_day is not None
                                and not group.project.allow_submissions_past_limit)
        if (has_hard_daily_limit
                and group.num_submits_towards_limit >= group.project.submission_limit_per_day):
            raise exceptions.ValidationError(
                {'submission': 'Submissions past the daily limit are '
                               'not allowed for this project'})

        if group.project.total_submission_limit is not None:
            submits_toward_total_limit = group.submissions.filter(
                count_towards_total_limit=True
            ).count()
            # Use >= in case of user error (if they forgot to set the submission
            # limit and some users already used up their submissions.
            if submits_toward_total_limit >= group.project.total_submission_limit:
                raise exceptions.ValidationError(
                    {'submission': 'This project does not allow more than '
                                   f'{group.project.total_submission_limit} submissions'}
                )


class SubmissionDetailViewSet(mixins.RetrieveModelMixin,
                              transaction_mixins.TransactionPartialUpdateMixin,
                              AGModelGenericViewSet):
    model_manager = ag_models.Submission.objects.select_related(
        'group__project__course')

    serializer_class = ag_serializers.SubmissionSerializer
    permission_classes = ((P(ag_permissions.is_admin()) | P(ag_permissions.IsReadOnly)),
                          ag_permissions.can_view_project(),
                          ag_permissions.is_staff_or_group_member())

    @swagger_auto_schema(
        manual_parameters=[
            Parameter(
                name='filename', in_='query',
                description='The name of the file to return.',
                required=True, type='str')
        ],
        responses={'200': 'Returns the file contents.'})
    @method_decorator(require_query_params('filename'))
    @decorators.detail_route()
    def file(self, request, *args, **kwargs):
        submission = self.get_object()
        filename = request.query_params['filename']
        try:
            return FileResponse(submission.get_file(filename))
        except ObjectDoesNotExist:
            return response.Response('File "{}" not found'.format(filename),
                                     status=status.HTTP_404_NOT_FOUND)

    @swagger_auto_schema(responses={'204': 'The submission has been removed from the queue.'},
                         request_body_parameters=[])
    @transaction.atomic()
    @decorators.detail_route(
        methods=['post'],
        # NOTE: Only group members can remove their own submissions from the queue.
        permission_classes=(ag_permissions.can_view_project(), ag_permissions.is_group_member()))
    def remove_from_queue(self, request, *args, **kwargs):
        """
        Remove this submission from the grading queue.
        """
        submission = self.get_object()
        removeable_statuses = [ag_models.Submission.GradingStatus.received,
                               ag_models.Submission.GradingStatus.queued]
        if submission.status not in removeable_statuses:
            return response.Response('This submission is not currently queued',
                                     status=status.HTTP_400_BAD_REQUEST)

        submission.status = (
            ag_models.Submission.GradingStatus.removed_from_queue)
        submission.save()

        return response.Response(status=status.HTTP_204_NO_CONTENT)
