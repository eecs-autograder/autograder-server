from rest_framework import viewsets, mixins, permissions, exceptions

import autograder.core.models as ag_models
import autograder.rest_api.serializers as ag_serializers

from ..permission_components import user_can_view_group, user_can_request_feedback_type
from ..load_object_mixin import build_load_object_mixin


class _Permissions(permissions.BasePermission):
    def has_object_permission(self, request, view, submission):
        return (user_can_view_group(request.user, submission.submission_group) and
                user_can_request_feedback_type(
                    request.user, request.query_params.get('feedback_type'), submission))


class SubmissionResultsViewset(
        build_load_object_mixin(ag_models.Submission, pk_key='submission_pk'),
        mixins.ListModelMixin,
        viewsets.GenericViewSet):
    permission_classes = (permissions.IsAuthenticated, _Permissions)

    def get_serializer(self, *args, **kwargs):
        if 'feedback_type' not in self.request.query_params:
            raise exceptions.ValidationError(
                {'feedback_type': 'Missing required query param: feedback_type'})

        fdbk_type = self.request.query_params.get('feedback_type')

        kwargs['context'] = self.get_serializer_context()
        return ag_serializers.AGTestResultSerializer(
            *args, feedback_type=fdbk_type, **kwargs)

    def get_queryset(self):
        submission = self.get_object()

        fdbk_type = self.request.query_params.get('feedback_type')
        if fdbk_type == 'normal':
            return submission.results.filter(test_case__visible_to_students=True)

        if fdbk_type == 'past_submission_limit':
            return submission.results.filter(
                test_case__visible_in_past_limit_submission=True)

        if fdbk_type == 'ultimate_submission':
            return submission.results.filter(
                test_case__visible_in_ultimate_submission=True)

        if fdbk_type == 'staff_viewer' or fdbk_type == 'max':
            return submission.results.all()

        raise exceptions.ValidationError(
            {'feedback_type': 'Invalid feedback_type: {}'.format(fdbk_type)})
