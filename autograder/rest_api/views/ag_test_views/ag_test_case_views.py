import autograder.core.models as ag_models
import autograder.rest_api.serializers as ag_serializers
import autograder.rest_api.permissions as ag_permissions

from autograder.rest_api.views.ag_model_views import (
    AGModelGenericViewSet, ListCreateNestedModelView, TransactionRetrieveUpdateDestroyMixin)


class AGTestCaseListCreateView(ListCreateNestedModelView):
    serializer_class = ag_serializers.AGTestCaseSerializer
    permission_classes = [
        ag_permissions.is_admin_or_read_only_staff(
            lambda ag_test_suite: ag_test_suite.project.course)
    ]

    pk_key = 'ag_test_suite_pk'
    model_manager = ag_models.AGTestSuite.objects.select_related('project__course')
    foreign_key_field_name = 'ag_test_suite'
    reverse_foreign_key_field_name = 'ag_test_cases'


class AGTestCaseDetailViewSet(TransactionRetrieveUpdateDestroyMixin, AGModelGenericViewSet):
    serializer_class = ag_serializers.AGTestCaseSerializer
    permission_classes = [
        ag_permissions.is_admin_or_read_only_staff(
            lambda ag_test_case: ag_test_case.ag_test_suite.project.course
        )
    ]
    model_manager = ag_models.AGTestCase.objects.select_related(
        'ag_test_suite__project__course',
        'normal_fdbk_config',
        'ultimate_submission_fdbk_config',
        'past_limit_submission_fdbk_config',
        'staff_viewer_fdbk_config',
    )
