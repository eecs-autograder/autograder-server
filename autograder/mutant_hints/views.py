import zoneinfo
from django.utils.decorators import method_decorator
from django.db import transaction
from django.db.models.signals import post_delete, post_save
from django.dispatch import receiver
from django.core.exceptions import ObjectDoesNotExist
from django.utils import timezone
from drf_composable_permissions.p import P
from rest_framework import response, status
from rest_framework.exceptions import ValidationError
from rest_framework.views import APIView
from django.http import Http404

import autograder.utils.testing as test_ut
import autograder.core.models as ag_models
import autograder.rest_api.permissions as ag_permissions
from autograder.rest_api.schema import (
    AGDetailViewSchemaGenerator,
    AGListCreateViewSchemaGenerator,
    APITags,
    register_api_object_type_name,
)
from autograder.rest_api.schema.view_schema_generators import AGListViewSchemaMixin, AGPatchViewSchemaMixin, AGViewSchemaGenerator
from autograder.rest_api.views.ag_model_views import (
    AGModelAPIView,
    AGModelDetailView,
    NestedModelView,
    convert_django_validation_error,
    handle_object_does_not_exist_404,
    require_body_params,
    require_non_null_body_params,
)
import autograder.core.utils as core_ut

from .models import MutationTestSuiteHintConfig, UnlockedHint

# CRUD for mutant test suite hence config, admin only

register_api_object_type_name(MutationTestSuiteHintConfig)
register_api_object_type_name(UnlockedHint)


class MutationTestSuiteHintConfigGetCreateView(NestedModelView):
    schema = AGListCreateViewSchemaGenerator(
        [APITags.mutation_test_suites], MutationTestSuiteHintConfig,
    )

    permission_classes = [
        ag_permissions.is_admin(lambda suite: suite.project.course)
    ]

    pk_key = 'mutation_test_suite_pk'
    model_manager = ag_models.MutationTestSuite.objects.select_related('project__course')
    nested_field_name = 'mutation_test_suite_hint_config'
    parent_obj_field_name = 'mutation_test_suite'

    def get(self, *args, **kwargs):
        suite = self.get_object()
        try:
            config = suite.mutation_test_suite_hint_config
        except ObjectDoesNotExist:
            raise Http404(
                f'Mutation test suite "{suite.name}" has no hint configuration'
            )

        return response.Response(config.to_dict())

    @convert_django_validation_error
    @transaction.atomic
    def post(self, *args, **kwargs):
        data = dict(self.request.data)
        data[self.parent_obj_field_name] = self.get_object()

        config = MutationTestSuiteHintConfig.objects.validate_and_create(**data)
        return response.Response(config.to_dict(), status.HTTP_201_CREATED)


class MutationTestSuiteHintConfigDetailView(AGModelDetailView):
    schema = AGDetailViewSchemaGenerator(tags=[APITags.mutation_test_suites])

    permission_classes = [
        ag_permissions.is_admin(
            lambda hint_config: hint_config.mutation_test_suite.project.course)
    ]
    model_manager = MutationTestSuiteHintConfig.objects.select_related(
        'mutation_test_suite__project__course')

    def get(self, *args, **kwargs):
        return self.do_get()

    def patch(self, *args, **kwargs):
        return self.do_patch()

    def delete(self, *args, **kwargs):
        return self.do_delete()


class UnlockedMutantHintsView(NestedModelView):
    schema = AGListCreateViewSchemaGenerator(
        [APITags.mutation_test_suites], UnlockedHint
    )

    is_staff = P(ag_permissions.is_staff(lambda result: result.mutation_test_suite.project.course))
    is_read_only_staff = P(ag_permissions.IsReadOnly) & is_staff
    is_group_member = P(ag_permissions.is_group_member(lambda result: result.submission.group))
    can_view_project = ag_permissions.can_view_project(
        lambda result: result.mutation_test_suite.project)

    is_group_member_and_normal_submission = (
        is_group_member
        & ag_permissions.can_request_feedback_category(
            lambda result: result.submission,
            feedback_category=ag_models.FeedbackCategory.normal,
        )
    )

    permission_classes = [
        (is_staff & is_group_member)
        | (is_group_member_and_normal_submission & can_view_project)
        | is_read_only_staff
    ]

    pk_key = 'mutation_test_suite_result_pk'
    model_manager = ag_models.MutationTestSuiteResult.objects.select_related(
        'submission__group__project__course')
    nested_field_name = 'unlocked_hints'

    def get(self, *args, **kwargs):
        """Load hints unlocked for the requested mutation test suite."""
        result: ag_models.MutationTestSuiteResult = self.get_object()
        query = UnlockedHint.objects.filter(
            mutation_test_suite_result__submission__group=result.submission.group,
            mutation_test_suite_hint_config__mutation_test_suite=result.mutation_test_suite,
            mutant_name=_get_first_undetected_bug(result),
        )
        return response.Response(
            data=[self.serialize_object(obj) for obj in query],
            status=status.HTTP_200_OK,
        )

    @handle_object_does_not_exist_404
    @convert_django_validation_error
    @transaction.atomic
    def post(self, *args, **kwargs):
        """Request a hint"""
        result: ag_models.MutationTestSuiteResult = self.get_object()

        locked_group = ag_models.Group.objects.select_for_update().get(pk=result.submission.group_id)
        test_ut.mocking_hook()

        hint_config = MutationTestSuiteHintConfig.objects.get(
            mutation_test_suite=result.mutation_test_suite
        )

        self._check_hint_limits(result, hint_config)

        first_undetected = _get_first_undetected_bug(result)
        if first_undetected is None:
            return response.Response(status=status.HTTP_204_NO_CONTENT)

        latest_hint = UnlockedHint.objects.filter(
            mutation_test_suite_result__submission__group=locked_group,
            mutant_name=first_undetected
        ).order_by('hint_number').last()

        next_hint_index = 0 if latest_hint is None else latest_hint.hint_number + 1
        available_hints = hint_config.hints_by_mutant_name.get(first_undetected, [])

        if next_hint_index >= len(available_hints):
            return response.Response(status=status.HTTP_204_NO_CONTENT)

        hint_text = available_hints[next_hint_index]

        queryset = self.get_nested_manager()
        new_hint = queryset.validate_and_create(
            mutation_test_suite_result=result,
            mutation_test_suite_hint_config=hint_config,
            mutant_name=first_undetected,
            hint_number=next_hint_index,
            hint_text=hint_text,
            unlocked_by=self.request.user.username,
        )
        return response.Response(
            data=self.serialize_object(new_hint),
            status=status.HTTP_201_CREATED
        )

    def _check_hint_limits(
        self,
        result: ag_models.MutationTestSuiteResult,
        hint_config: MutationTestSuiteHintConfig
    ):
        num_hints_for_submission = get_num_hints_for_submission(result.mutation_test_suite, result.submission)
        if (hint_config.num_hints_per_submission is not None
                and num_hints_for_submission >= hint_config.num_hints_per_submission):
            raise ValidationError({
                '__all__': f'{num_hints_for_submission}/{hint_config.num_hints_per_submission} '
                           'hints already unlocked for this submission.'
            })

        num_hints_today = get_num_hints_today(result.submission.group, hint_config)
        if (hint_config.num_hints_per_day is not None
                and num_hints_today >= hint_config.num_hints_per_day):
            raise ValidationError({
                '__all__': f'{num_hints_today}/{hint_config.num_hints_per_day} '
                           'hints already unlocked today.'
            })


class NumMutantHintsAvailableView(AGModelDetailView):
    # FIXME: Custom schema generator

    permission_classes = UnlockedMutantHintsView.permission_classes
    model_manager = ag_models.MutationTestSuiteResult.objects.select_related(
        'submission__group__project__course')
    pk_key = 'mutation_test_suite_result_pk'

    @handle_object_does_not_exist_404
    def get(self, *args, **kwargs):
        result: ag_models.MutationTestSuiteResult = self.get_object()
        first_undetected = _get_first_undetected_bug(result)
        hint_config = MutationTestSuiteHintConfig.objects.get(
            mutation_test_suite=result.mutation_test_suite
        )
        num_hints_remaining = get_num_locked_hints_remaining(
            result.submission.group,
            hint_config,
            first_undetected
        )
        return response.Response({
            'num_hints_remaining': num_hints_remaining,
            # FIXME: Obfuscation
            'mutant_name': first_undetected,
        })


def _get_first_undetected_bug(result: ag_models.MutationTestSuiteResult) -> str | None:
    undetected_bugs = [
        bug for bug in result.mutation_test_suite.buggy_impl_names
        if bug not in result.bugs_exposed
    ]
    return None if not undetected_bugs else undetected_bugs[0]


def get_num_hints_for_submission(
    mutation_test_suite: ag_models.MutationTestSuite,
    submission: ag_models.Submission,
) -> int:
    return UnlockedHint.objects.filter(
        mutation_test_suite_result__submission=submission,
        mutation_test_suite_result__mutation_test_suite=mutation_test_suite
    ).count()


def get_num_hints_today(group: ag_models.Group, hint_config: MutationTestSuiteHintConfig) -> int:
    start_datetime, end_datetime = core_ut.get_24_hour_period(
        hint_config.hint_limit_reset_time,
        timezone.now().astimezone(
            zoneinfo.ZoneInfo(hint_config.hint_limit_reset_timezone)
        )
    )
    return UnlockedHint.objects.filter(
        mutation_test_suite_result__submission__group=group,
        mutation_test_suite_hint_config=hint_config,
        created_at__gte=start_datetime, created_at__lt=end_datetime).count()


def get_num_locked_hints_remaining(
    group: ag_models.Group,
    hint_config: MutationTestSuiteHintConfig,
    mutant_name: str
):
    latest_hint = (
        UnlockedHint.objects.filter(
            mutation_test_suite_result__submission__group=group,
            mutant_name=mutant_name).order_by('hint_number').last()
    )
    total_num_hints = len(hint_config.hints_by_mutant_name.get(mutant_name, []))
    if latest_hint is None:
        return total_num_hints

    num_hints_unlocked = latest_hint.hint_number + 1

    return max(0, total_num_hints - num_hints_unlocked)


class AllUnlockedHintsView(AGModelAPIView):
    class _SchemaGenerator(AGListViewSchemaMixin, AGViewSchemaGenerator):
        pass

    schema = _SchemaGenerator(
        [APITags.mutation_test_suites], UnlockedHint
    )

    pk_key = 'group_pk'
    model_manager = ag_models.Group.objects.select_related('project__course')

    permission_classes = [
        ag_permissions.can_view_project(),
        ag_permissions.is_staff_or_group_member()
    ]

    def get(self, *args, **kwargs):
        group = self.get_object()
        hints = UnlockedHint.objects.filter(mutation_test_suite_result__submission__group=group)

        return response.Response(data=[hint.to_dict() for hint in hints])


class RateHintView(AGModelDetailView):
    class _SchemaGenerator(AGPatchViewSchemaMixin, AGViewSchemaGenerator):
        pass

    # FIXME: custom body with CustomViewSchema
    schema = _SchemaGenerator(
        [APITags.mutation_test_suites], UnlockedHint
    )

    model_manager = UnlockedHint.objects.select_related(
        'mutation_test_suite_result__submission__group__project__course')

    permission_classes = [
        ag_permissions.can_view_project(
            lambda hint: hint.mutation_test_suite_result.submission.group.project),
        ag_permissions.is_group_member(
            lambda hint: hint.mutation_test_suite_result.submission.group),
    ]

    @method_decorator(require_non_null_body_params('hint_rating'))
    @method_decorator(require_body_params('hint_rating'))
    def patch(self, *args, **kwargs):
        return self.do_patch()


class DailyHintLimitView(AGModelAPIView):
    # FIXME: Custom response schema

    pk_key = 'group_pk'
    model_manager = ag_models.Group.objects.select_related('project__course')

    permission_classes = [
        ag_permissions.can_view_project(),
        ag_permissions.is_staff_or_group_member(),
    ]

    # FIXME: This needs to either include limits for all the mutation test suites
    # or take in the PK of the particular suite in addition to the group PK
    @handle_object_does_not_exist_404
    @transaction.atomic
    def get(self, *args, **kwargs):
        group = self.get_object()
        hint_config = MutationTestSuiteHintConfig.objects.get(mutation_test_suite__project=group.project)
        return response.Response(
            data={
                'num_hints_unlocked_today': get_num_hints_today(group, hint_config),
                'num_hints_per_day': hint_config.num_hints_per_day,
            }
        )


class HintLimitView(AGModelAPIView):
    # FIXME: Custom response schema

    pk_key = 'mutation_test_suite_result_pk'
    model_manager = ag_models.MutationTestSuiteResult.objects.select_related(
        'submission__group__project__course',
        'mutation_test_suite'
    )

    permission_classes = [
        ag_permissions.can_view_project(lambda result: result.submission.project),
        ag_permissions.is_staff_or_group_member(lambda result: result.submission.group),
    ]

    @handle_object_does_not_exist_404
    @transaction.atomic
    def get(self, *args, **kwargs):
        result = self.get_object()
        hint_config = MutationTestSuiteHintConfig.objects.get(
            mutation_test_suite=result.mutation_test_suite)
        return response.Response(
            data={
                'num_hints_unlocked': {
                    'submission': get_num_hints_for_submission(
                        result.mutation_test_suite, result.submission),
                    'today': get_num_hints_today(result.submission.group, hint_config),
                },
                'num_hints_allowed': {
                    'submission': hint_config.num_hints_per_submission,
                    'today': hint_config.num_hints_per_day,
                },
            }
        )


# unlock next hint for student,
#   - takes in mutation test suite result
#   - only allowed on submission eligible for normal feedback
#   - check against number of hints unlocked today
#   - check against number of hints unlocked for this submission
#   - check deadline not passed (add this later)
#   - check to make sure there is at least one locked hint for the first undetected mutant
#   - only allowed for group numbers

# load unlocked hints for mutation test suite result
# - get number of locked hints available for the mutant

# Hint limits view
# include number of submissions on locked towards per day and per submission limits
#   (include number unlocked and the limit numbers)

# all unlocked hints for group
