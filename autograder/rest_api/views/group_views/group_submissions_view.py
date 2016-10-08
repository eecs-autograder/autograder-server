from django.db import transaction
from django.utils import timezone

from rest_framework import viewsets, mixins, permissions, exceptions

import autograder.core.models as ag_models
import autograder.rest_api.serializers as ag_serializers

from ..permission_components import user_can_view_group
from ..load_object_mixin import build_load_object_mixin


class _Permissions(permissions.BasePermission):
    def has_object_permission(self, request, view, group):
        # We want the timestamp to be immediately when the request is
        # being processed.
        timestamp = timezone.now()

        if request.method.lower() == 'get':
            return user_can_view_group(request.user, group)

        if request.method.lower() == 'post':
            return self._has_submit_permission(request, view, group, timestamp)

        return False

    def _has_submit_permission(self, request, view, group, timestamp):
        if not user_can_view_group(request.user, group):
            return False

        return group.members.filter(pk=request.user.pk).exists()


class GroupSubmissionsViewset(
        build_load_object_mixin(ag_models.SubmissionGroup, pk_key='group_pk'),
        mixins.ListModelMixin,
        mixins.CreateModelMixin,
        viewsets.GenericViewSet):
    serializer_class = ag_serializers.SubmissionSerializer
    permission_classes = (permissions.IsAuthenticated, _Permissions)

    def get_queryset(self):
        return self.get_object().submissions.all()

    @transaction.atomic()
    def create(self, request, *args, **kwargs):
        timestamp = timezone.now()
        group = self.get_object()
        self._validate_can_submit(request, group, timestamp)
        return super().create(request, *args, **kwargs)

    def perform_create(self, serializer):
        serializer.save(submission_group=self.get_object(),
                        submitter=self.request.user.username)

    def _validate_can_submit(self, request, group, timestamp):
        has_active_submission = group.submissions.filter(
            status__in=ag_models.Submission.GradingStatus.active_statuses
        ).exists()
        if has_active_submission:
            raise exceptions.ValidationError(
                {'submission': 'Unable to resubmit while current submission is being processed'})

        # Provided they don't have a submission being processed, staff
        # should always be able to submit.
        if (group.project.course.is_course_staff(request.user) and
                group.members.filter(pk=request.user.pk).exists()):
            return

        if group.project.disallow_student_submissions:
            raise exceptions.ValidationError(
                {'submission': 'Submitting has been temporarily disabled for this project'})

        closing_time = group.extended_due_date
        if closing_time is None:
            closing_time = group.project.closing_time
        deadline_past = (closing_time is not None and
                         timestamp > closing_time)

        if deadline_past:
            raise exceptions.ValidationError(
                {'submission': 'The closing time for this project has passed'})

        if (group.project.submission_limit_per_day is None or
                group.project.allow_submissions_past_limit):
            return

        if (group.num_submits_towards_limit >=
                group.project.submission_limit_per_day):
            raise exceptions.ValidationError(
                {'submission': 'Unable to resubmit while current submission is being processed'})
