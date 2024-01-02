from datetime import datetime, timedelta, timezone, time
import tempfile
from pathlib import Path
from typing import Optional
from unittest import mock

from django.contrib.auth.models import User
from django.conf import settings
from django.core import exceptions
from django.core.exceptions import ObjectDoesNotExist
from django.db import connection
from django.db.models.signals import post_save
from django.test import tag
from django.test.utils import override_settings
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APIClient

import autograder.core.models as ag_models
import autograder.handgrading.models as hg_models
from autograder.mutant_hints.models import MutationTestSuiteHintConfig, UnlockedHint
import autograder.utils.testing.model_obj_builders as obj_build
from autograder.rest_api.signals import on_project_created
from autograder.rest_api.tests.test_views.ag_view_test_base import AGViewTestBase
from autograder.utils import exclude_dict
from autograder.utils.testing import UnitTestBase
import autograder.utils.testing as test_ut

class MutationTestSuiteHintConfigGetCreateViewTestCase(AGViewTestBase):
    def setUp(self) -> None:
        super().setUp()

        self.mutation_test_suite = obj_build.make_mutation_test_suite()
        self.project = self.mutation_test_suite.project
        self.client = APIClient()
        self.admin = obj_build.make_admin_user(self.project.course)
        self.url = reverse(
            'mutation-test-suite-hint-config',
            kwargs={'mutation_test_suite_pk': self.mutation_test_suite.pk}
        )

    def test_admin_get_config(self) -> None:
        config = MutationTestSuiteHintConfig.objects.validate_and_create(
            mutation_test_suite=self.mutation_test_suite
        )

        self.client.force_authenticate(self.admin)
        response = self.client.get(self.url)

        self.assertEqual(config.to_dict(), response.data)

    def test_admin_create_config(self) -> None:
        self.do_create_object_test(
            MutationTestSuiteHintConfig.objects, self.client, self.admin, self.url, {})

    def test_non_admin_get_config_forbidden(self) -> None:
        config = MutationTestSuiteHintConfig.objects.validate_and_create(
            mutation_test_suite=self.mutation_test_suite
        )

        staff = obj_build.make_staff_user(self.project.course)
        self.do_permission_denied_get_test(self.client, staff, self.url)

        student = obj_build.make_student_user(self.project.course)
        self.do_permission_denied_get_test(self.client, student, self.url)

    def test_non_admin_create_config_forbidden(self) -> None:
        staff = obj_build.make_staff_user(self.project.course)
        self.do_permission_denied_create_test(
            MutationTestSuiteHintConfig.objects, self.client, staff, self.url, {})

        student = obj_build.make_student_user(self.project.course)
        self.do_permission_denied_create_test(
            MutationTestSuiteHintConfig.objects, self.client, student, self.url, {})

    def test_get_config_does_not_exist(self) -> None:
        self.do_get_request_404_test(self.client, self.admin, self.url)


class MutationTestSuiteHintConfigDetailViewTestCase(AGViewTestBase):
    def setUp(self) -> None:
        super().setUp()

        self.mutation_test_suite = obj_build.make_mutation_test_suite()
        self.project = self.mutation_test_suite.project
        self.config = MutationTestSuiteHintConfig.objects.validate_and_create(
            mutation_test_suite=self.mutation_test_suite
        )

        self.client = APIClient()
        self.admin = obj_build.make_admin_user(self.project.course)
        self.staff = obj_build.make_staff_user(self.project.course)
        self.student = obj_build.make_student_user(self.project.course)
        self.url = reverse(
            'mutation-test-suite-hint-config-detail',
            kwargs={'pk': self.config.pk}
        )

    def test_admin_get_config(self) -> None:
        self.do_get_object_test(self.client, self.admin, self.url, self.config.to_dict())

    def test_admin_update_config(self) -> None:
        self.do_patch_object_test(
            self.config, self.client, self.admin, self.url,
            {
                'hints_by_mutant_name': {'mut1': ['hint1', 'hint2']},
                'num_hints_per_day': 4,
                'hint_limit_reset_time': time(11, 50, 00),
                'hint_limit_reset_timezone': 'America/Chicago',
                'num_hints_per_submission': 10,
                'obfuscate_mutant_names': True,
            }
        )

    def test_admin_update_config_invalid_args(self) -> None:
        self.do_patch_object_invalid_args_test(
            self.config, self.client, self.admin, self.url,
            {
                'hints_by_mutant_name': {'spam': [42]},
                'num_hints_per_day': 0,
                'num_hints_per_submission': 0,
            }
        )

    def test_admin_delete_config(self) -> None:
        self.do_delete_object_test(self.config, self.client, self.admin, self.url)

    def test_non_admin_get_config_fordibben(self) -> None:
        self.do_permission_denied_get_test(self.client, self.staff, self.url)
        self.do_permission_denied_get_test(self.client, self.student, self.url)

    def test_non_admin_update_config_fordibben(self) -> None:
        self.do_patch_object_permission_denied_test(
            self.config, self.client, self.staff, self.url, {'num_hints_per_day': 1000})

        self.do_patch_object_permission_denied_test(
            self.config, self.client, self.student, self.url, {'num_hints_per_day': 1000})

    def test_non_admin_delete_config_fordibben(self) -> None:
        self.do_delete_object_permission_denied_test(
            self.config, self.client, self.staff, self.url)
        self.do_delete_object_permission_denied_test(
            self.config, self.client, self.student, self.url)


class _UnlockedHintSetUp(AGViewTestBase):
    def setUp(self) -> None:
        super().setUp()

        self.client = APIClient()

        self.project = obj_build.make_project(visible_to_students=True)
        self.course = self.project.course

        self.group1 = obj_build.make_group(project=self.project)
        self.group1_submission1 = obj_build.make_finished_submission(group=self.group1)
        self.group1_submission2 = obj_build.make_finished_submission(group=self.group1)
        self.group1_submission3 = obj_build.make_finished_submission(group=self.group1)

        self.group2 = obj_build.make_group(project=self.project)
        self.group2_submission1 = obj_build.make_finished_submission(self.group2)

        self.mutation_test_suite = obj_build.make_mutation_test_suite(
            self.project,
            buggy_impl_names=['mut1', 'mut2', 'mut3_no_hints', 'mut4']
        )
        self.config = MutationTestSuiteHintConfig.objects.validate_and_create(
            mutation_test_suite=self.mutation_test_suite,
            hints_by_mutant_name={
                'mut1': ['hint1'],
                'mut2': ['some mut2 hint', 'other mut2 hint', 'more mut2 hint'],
                'mut3_no_hints': [],
            }
        )

        self.mutation_test_suite2 = obj_build.make_mutation_test_suite(
            self.project,
            buggy_impl_names=['suite2_mut1']
        )
        self.config2 = MutationTestSuiteHintConfig.objects.validate_and_create(
            mutation_test_suite=self.mutation_test_suite2,
            hints_by_mutant_name={
                'suite2_mut1': ['a super hint1'],
            }
        )

    def get_result_hints_url(self, result: ag_models.MutationTestSuiteResult) -> str:
        return reverse(
            'mutation-test-suite-unlocked-hints',
            kwargs={'mutation_test_suite_result_pk': result.pk}
        )

    def get_group_hints_url(self, group: ag_models.Group) -> str:
        return reverse(
            'all-unlocked-mutant-hints',
            kwargs={'group_pk': group.pk}
        )

    def do_unlock_hint_test(
        self,
        suite: ag_models.MutationTestSuite,
        group: ag_models.Group,
        *,
        user: User | None = None,
        submission: ag_models.Submission | None = None,
        result: ag_models.MutationTestSuiteResult | None = None,
        bugs_detected: list[str] = [],
        expected_hint_text: str | None = None,
        expected_hint_number: int | None = None,
        expected_response_status: int = status.HTTP_201_CREATED
    ):
        if user is None:
            user = group.members.first()

        if result is None:
            result = ag_models.MutationTestSuiteResult.objects.validate_and_create(
                mutation_test_suite=suite,
                submission=(
                    submission if submission is not None else obj_build.make_submission(group)),
                bugs_exposed=bugs_detected,
            )

        self.client.force_authenticate(user)
        response = self.client.post(self.get_result_hints_url(result))
        self.assertEqual(expected_response_status, response.status_code)

        if expected_response_status == status.HTTP_204_NO_CONTENT:
            self.assertIsNone(response.data)
        else:
            self.assertEqual(expected_hint_text, response.data['hint_text'])
            self.assertEqual(expected_hint_number, response.data['hint_number'])
            # FIXME: check mutant name

            loaded = UnlockedHint.objects.get(pk=response.data['pk'])
            self.assertEqual(user.username, loaded.unlocked_by)

        return result

    def do_permission_denied_unlock_hint_test(
        self,
        user: User,
        group: ag_models.Group,
        suite: ag_models.MutationTestSuite,
        submission: ag_models.Submission | None = None
    ) -> None:
        queryset = UnlockedHint.objects.filter(mutation_test_suite_result__submission__group=group)
        original_num = queryset.count()
        result = ag_models.MutationTestSuiteResult.objects.validate_and_create(
                mutation_test_suite=suite,
                submission=(
                    submission if submission is not None else obj_build.make_submission(group)
                ),
        )

        self.client.force_authenticate(user)
        response = self.client.post(self.get_result_hints_url(result))
        self.assertEqual(status.HTTP_403_FORBIDDEN, response.status_code, msg=response.data)
        self.assertEqual(original_num, queryset.count())

    def do_bad_request_unlock_hint_test(
        self,
        group: ag_models.Group,
        result: ag_models.MutationTestSuiteResult,
    ) -> None:
        queryset = UnlockedHint.objects.filter(mutation_test_suite_result__submission__group=group)
        original_num = queryset.count()

        self.client.force_authenticate(group.members.first())
        response = self.client.post(self.get_result_hints_url(result))
        self.assertEqual(status.HTTP_400_BAD_REQUEST, response.status_code, msg=response.data)
        self.assertEqual(original_num, queryset.count())
        return response

    def check_num_hints_towards_daily_limit(
        self,
        result: ag_models.MutationTestSuiteResult,
        expected_num_hints_unlocked: int | None,
        expected_hints_per_day: int | None,
        *,
        user: User | None = None,
    ) -> None:
        if user is None:
            user = result.submission.group.members.first()

        self.client.force_authenticate(user)
        url = reverse(
            'mutant-hint-limits', kwargs={'mutation_test_suite_result_pk': result.pk})
        response = self.client.get(url)
        self.assertEqual(status.HTTP_200_OK, response.status_code)
        self.assertEqual(expected_num_hints_unlocked, response.data['num_hints_unlocked']['today'])
        self.assertEqual(expected_hints_per_day, response.data['num_hints_allowed']['today'])

    def check_num_hints_towards_submission_limit(
        self,
        result: ag_models.MutationTestSuiteResult,
        expected_num_hints_unlocked: int | None,
        expected_hints_per_submission: int | None,
        *,
        user: User | None = None,
    ) -> None:
        if user is None:
            user = result.submission.group.members.first()

        self.client.force_authenticate(user)
        url = reverse(
            'mutant-hint-limits', kwargs={'mutation_test_suite_result_pk': result.pk})
        response = self.client.get(url)
        self.assertEqual(status.HTTP_200_OK, response.status_code)
        self.assertEqual(
            expected_num_hints_unlocked, response.data['num_hints_unlocked']['submission'])
        self.assertEqual(
            expected_hints_per_submission, response.data['num_hints_allowed']['submission'])


class UnlockedMutantHintsViewGetHintListTestCase(_UnlockedHintSetUp):
    def setUp(self) -> None:
        super().setUp()

        self.mutation_test_suite2 = obj_build.make_mutation_test_suite(
            self.project,
            buggy_impl_names=['suite2_mut1']
        )
        self.config2 = MutationTestSuiteHintConfig.objects.validate_and_create(
            mutation_test_suite=self.mutation_test_suite2,
            hints_by_mutant_name={
                'suite2_mut1': ['a super hint1'],
            }
        )

        self.group1_submission1_result1 = ag_models.MutationTestSuiteResult.objects.validate_and_create(
            mutation_test_suite=self.mutation_test_suite,
            submission=self.group1_submission1,
            bugs_exposed=['mut1'],
        )
        self.group1_submission1_result1_hint = UnlockedHint.objects.validate_and_create(
            mutation_test_suite_result=self.group1_submission1_result1,
            mutation_test_suite_hint_config=self.config,
            mutant_name='mut2',
            hint_number=0,
            hint_text='some mut2 hint',
        )
        self.group1_submission1_result1_hint2 = UnlockedHint.objects.validate_and_create(
            mutation_test_suite_result=self.group1_submission1_result1,
            mutation_test_suite_hint_config=self.config,
            mutant_name='mut2',
            hint_number=1,
            hint_text='other mut2 hint',
        )

        self.group1_submission2_result2 = ag_models.MutationTestSuiteResult.objects.validate_and_create(
            mutation_test_suite=self.mutation_test_suite2,
            submission=self.group1_submission2,
            bugs_exposed=[],
        )
        self.group1_submission2_result2_hint = UnlockedHint.objects.validate_and_create(
            mutation_test_suite_result=self.group1_submission2_result2,
            mutation_test_suite_hint_config=self.config2,
            mutant_name='suite2_mut1',
            hint_number=0,
            hint_text='a super hint1',
        )

        self.group2_submission1_result = ag_models.MutationTestSuiteResult.objects.validate_and_create(
            mutation_test_suite=self.mutation_test_suite,
            submission=self.group2_submission1,
            bugs_exposed=[],
        )
        self.group2_submission1_result_hint = UnlockedHint.objects.validate_and_create(
            mutation_test_suite_result=self.group2_submission1_result,
            mutation_test_suite_hint_config=self.config,
            mutant_name='mut1',
            hint_number=0,
            hint_text='hint1',
        )

    def test_student_get_group_hints(self) -> None:
        self.do_list_objects_test(
            self.client,
            self.group1.members.first(),
            self.get_group_hints_url(self.group1),
            [
                self.group1_submission1_result1_hint.to_dict(),
                self.group1_submission2_result2_hint.to_dict(),
                self.group1_submission1_result1_hint2.to_dict(),
            ]
        )

        self.do_list_objects_test(
            self.client,
            self.group2.members.first(),
            self.get_group_hints_url(self.group2),
            [
                self.group2_submission1_result_hint.to_dict(),
            ]
        )

    def test_student_get_result_hints(self) -> None:
        self.do_list_objects_test(
            self.client,
            self.group1.members.first(),
            self.get_result_hints_url(self.group1_submission1_result1),
            [
                self.group1_submission1_result1_hint.to_dict(),
                self.group1_submission1_result1_hint2.to_dict(),
            ]
        )
        self.do_list_objects_test(
            self.client,
            self.group1.members.first(),
            self.get_result_hints_url(self.group1_submission2_result2),
            [
                self.group1_submission2_result2_hint.to_dict(),
            ]
        )

        self.do_list_objects_test(
            self.client,
            self.group2.members.first(),
            self.get_result_hints_url(self.group2_submission1_result),
            [
                self.group2_submission1_result_hint.to_dict(),
            ]
        )

    def test_results_with_same_undetected_mutant_get_cumulative_hints(self) -> None:
        # Earlier and later submissions with the same 1st undectected mutant
        # should be shown all the hints unlocked for that mutant

        self.config.hints_by_mutant_name['mut1'].append('hint2')
        self.config.save()
        # Make sure that we're querying on the hint config and the mutant name
        self.mutation_test_suite2.buggy_impl_names.append('mut1')
        self.mutation_test_suite2.save()
        self.config2.hints_by_mutant_name['mut1'] = ['sneaky hint1']
        self.config2.save()

        group3 = obj_build.make_group(project=self.project)
        group3_submission1 = obj_build.make_finished_submission(group=group3)
        group3_submission2 = obj_build.make_finished_submission(group=group3)
        group3_submission3 = obj_build.make_finished_submission(group=group3)
        group3_submission4 = obj_build.make_finished_submission(group=group3)

        group3_submission1_result1 = ag_models.MutationTestSuiteResult.objects.validate_and_create(
            mutation_test_suite=self.mutation_test_suite,
            submission=group3_submission1,
            bugs_exposed=[],
        )

        # First hint unlocked here
        group3_submission2_result1 = ag_models.MutationTestSuiteResult.objects.validate_and_create(
            mutation_test_suite=self.mutation_test_suite,
            submission=group3_submission2,
            bugs_exposed=[],
        )
        group3_submission2_result1_hint = UnlockedHint.objects.validate_and_create(
            mutation_test_suite_result=group3_submission2_result1,
            mutation_test_suite_hint_config=self.config,
            mutant_name='mut1',
            hint_number=0,
            hint_text='hint1',
        )

        # 2nd hint unlocked here
        group3_submission3_result1 = ag_models.MutationTestSuiteResult.objects.validate_and_create(
            mutation_test_suite=self.mutation_test_suite,
            submission=group3_submission3,
            bugs_exposed=[],
        )
        group3_submission3_result1_hint = UnlockedHint.objects.validate_and_create(
            mutation_test_suite_result=group3_submission3_result1,
            mutation_test_suite_hint_config=self.config,
            mutant_name='mut1',
            hint_number=1,
            hint_text='hint2',
        )

        # Throw in a hint for the other mutation test suite so that we know
        # our query differentiates
        group3_submission3_result2 = ag_models.MutationTestSuiteResult.objects.validate_and_create(
            mutation_test_suite=self.mutation_test_suite2,
            submission=group3_submission3,
            bugs_exposed=['suite2_mut1'],
        )
        group3_submission3_result2_hint = UnlockedHint.objects.validate_and_create(
            mutation_test_suite_result=group3_submission3_result2,
            mutation_test_suite_hint_config=self.config2,
            mutant_name='mut1',
            hint_number=0,
            hint_text='sneaky hint1',
        )

        group3_submission4_result1 = ag_models.MutationTestSuiteResult.objects.validate_and_create(
            mutation_test_suite=self.mutation_test_suite,
            submission=group3_submission4,
            bugs_exposed=['mut1'],
        )
        group3_submission4_result1_hint = UnlockedHint.objects.validate_and_create(
            mutation_test_suite_result=group3_submission4_result1,
            mutation_test_suite_hint_config=self.config,
            mutant_name='mut2',
            hint_number=1,
            hint_text='some mut2 hint',
        )

        self.do_list_objects_test(
            self.client,
            group3.members.first(),
            self.get_result_hints_url(group3_submission1_result1),
            [
                group3_submission2_result1_hint.to_dict(),
                group3_submission3_result1_hint.to_dict(),
            ]
        )

        self.do_list_objects_test(
            self.client,
            group3.members.first(),
            self.get_result_hints_url(group3_submission2_result1),
            [
                group3_submission2_result1_hint.to_dict(),
                group3_submission3_result1_hint.to_dict(),
            ]
        )

        self.do_list_objects_test(
            self.client,
            group3.members.first(),
            self.get_result_hints_url(group3_submission3_result1),
            [
                group3_submission2_result1_hint.to_dict(),
                group3_submission3_result1_hint.to_dict(),
            ]
        )

        self.do_list_objects_test(
            self.client,
            group3.members.first(),
            self.get_result_hints_url(group3_submission3_result2),
            [
                group3_submission3_result2_hint.to_dict(),
            ]
        )

        self.do_list_objects_test(
            self.client,
            group3.members.first(),
            self.get_result_hints_url(group3_submission4_result1),
            [
                group3_submission4_result1_hint.to_dict(),
            ]
        )

    def test_staff_get_self_hints(self) -> None:
        self.project.course.staff.add(self.group2.members.first())

        self.do_list_objects_test(
            self.client,
            self.group2.members.first(),
            self.get_group_hints_url(self.group2),
            [
                self.group2_submission1_result_hint.to_dict(),
            ]
        )

        self.do_list_objects_test(
            self.client,
            self.group2.members.first(),
            self.get_result_hints_url(self.group2_submission1_result),
            [
                self.group2_submission1_result_hint.to_dict(),
            ]
        )

    def test_read_only_staff_get_other_group_hints(self) -> None:
        staff = obj_build.make_staff_user(self.project.course)

        self.do_list_objects_test(
            self.client,
            staff,
            self.get_group_hints_url(self.group2),
            [
                self.group2_submission1_result_hint.to_dict(),
            ]
        )

        self.do_list_objects_test(
            self.client,
            staff,
            self.get_result_hints_url(self.group2_submission1_result),
            [
                self.group2_submission1_result_hint.to_dict(),
            ]
        )

    def test_non_group_member_get_hints_forbidden(self) -> None:
        other_student = obj_build.make_student_user(self.course)

        self.do_permission_denied_get_test(
            self.client,
            other_student,
            self.get_group_hints_url(self.group2),
        )

        self.do_permission_denied_get_test(
            self.client,
            other_student,
            self.get_result_hints_url(self.group2_submission1_result),
        )

    def test_student_get_hints_submission_not_normal_forbidden(self) -> None:
        # Note: If a submission is past the daily limit, then students
        # would not have had an opportunity to unlock any hints for that submission.

        self.group2_submission1.is_past_daily_limit = True
        self.group2_submission1.save()

        self.do_permission_denied_get_test(
            self.client,
            self.group2.members.first(),
            self.get_result_hints_url(self.group2_submission1_result),
        )

    def test_obfuscated_mutant_names(self) -> None:
        self.fail()

    def test_project_hidden_forbidden(self) -> None:
        self.project.validate_and_update(visible_to_students=False)

        self.do_permission_denied_get_test(
            self.client,
            self.group2.members.first(),
            self.get_result_hints_url(self.group2_submission1_result),
        )

    def test_unlock_hints_no_hint_config_404(self) -> None:
        self.config.delete()
        self.client.force_authenticate(self.group1.members.first())

        url = reverse(
            'mutation-test-suite-unlocked-hints',
            kwargs={'mutation_test_suite_result_pk': self.group1_submission1_result1.pk}
        )
        response = self.client.post(url, {})
        self.assertEqual(status.HTTP_404_NOT_FOUND, response.status_code)


# Note: This suite also tests the hint limit endpoints
class UnlockedMutantHintsViewUnlockNewHintTestCase(_UnlockedHintSetUp):
    def test_student_unlock_all_hints_no_limit(self) -> None:
        # 1st mutant
        suite_result1 = self.do_unlock_hint_test(
            self.mutation_test_suite,
            self.group1,
            bugs_detected=[],
            expected_hint_text='hint1',
            expected_hint_number=0,
        )
        self.check_num_hints_towards_daily_limit(suite_result1, 1, None)
        self.check_num_hints_towards_submission_limit(suite_result1, 1, None)

        self.do_unlock_hint_test(
            self.mutation_test_suite,
            self.group1,
            result=suite_result1,
            expected_response_status=status.HTTP_204_NO_CONTENT
        )
        self.check_num_hints_towards_daily_limit(suite_result1, 1, None)
        self.check_num_hints_towards_submission_limit(suite_result1, 1, None)

        # 2nd mutant
        suite_result2 = self.do_unlock_hint_test(
            self.mutation_test_suite,
            self.group1,
            bugs_detected=['mut1'],
            expected_hint_text='some mut2 hint',
            expected_hint_number=0,
        )

        self.do_unlock_hint_test(
            self.mutation_test_suite,
            self.group1,
            result=suite_result2,
            expected_hint_text='other mut2 hint',
            expected_hint_number=1,
        )

        self.do_unlock_hint_test(
            self.mutation_test_suite,
            self.group1,
            result=suite_result2,
            expected_hint_text='more mut2 hint',
            expected_hint_number=2,
        )

        self.do_unlock_hint_test(
            self.mutation_test_suite,
            self.group1,
            result=suite_result2,
            expected_response_status=status.HTTP_204_NO_CONTENT
        )
        self.check_num_hints_towards_daily_limit(suite_result2, 4, None)
        self.check_num_hints_towards_submission_limit(suite_result2, 3, None)

        # 3rd mutant
        suite_result3 = self.do_unlock_hint_test(
            self.mutation_test_suite,
            self.group1,
            bugs_detected=['mut1', 'mut2'],
            expected_response_status=status.HTTP_204_NO_CONTENT
        )

        # Mutant from other suite
        suite_result4 = ag_models.MutationTestSuiteResult.objects.validate_and_create(
            mutation_test_suite=self.mutation_test_suite2,
            submission=suite_result3.submission,
            bugs_exposed=[],
        )
        self.do_unlock_hint_test(
            self.mutation_test_suite2,
            self.group1,
            result=suite_result4,
            expected_hint_text='a super hint1',
            expected_hint_number=0,
        )
        self.check_num_hints_towards_daily_limit(suite_result2, 4, None)
        self.check_num_hints_towards_daily_limit(suite_result4, 1, None)
        self.check_num_hints_towards_submission_limit(suite_result4, 1, None)

    def test_unlock_hint_mutant_name_not_in_dict(self) -> None:
        self.do_unlock_hint_test(
            self.mutation_test_suite,
            self.group1,
            bugs_detected=['mut1', 'mut2', 'mut3_no_hints'],
            expected_response_status=status.HTTP_204_NO_CONTENT
        )

    def test_staff_unlock_self_hint(self) -> None:
        self.course.staff.add(self.group1.members.first())
        self.do_unlock_hint_test(
            self.mutation_test_suite,
            self.group1,
            bugs_detected=[],
            expected_hint_text='hint1',
            expected_hint_number=0,
        )

    def test_staff_unlock_self_hint_hidden_project(self) -> None:
        self.project.validate_and_update(visible_to_students=False)
        self.project.refresh_from_db()
        staff_group = obj_build.make_group(
            members_role=obj_build.UserRole.staff, project=self.project)
        self.do_unlock_hint_test(
            self.mutation_test_suite,
            staff_group,
            bugs_detected=[],
            expected_hint_text='hint1',
            expected_hint_number=0,
        )

    def test_staff_unlock_other_group_hint_forbidden(self) -> None:
        staff = obj_build.make_staff_user(self.course)
        self.do_permission_denied_unlock_hint_test(staff, self.group1, self.mutation_test_suite)

    def test_non_group_member_unlock_hint_forbidden(self) -> None:
        other_student = obj_build.make_student_user(self.course)
        self.do_permission_denied_unlock_hint_test(other_student, self.group1, self.mutation_test_suite)

    def test_student_unlock_hint_submission_not_normal_forbidden(self) -> None:
        submission = obj_build.make_finished_submission(self.group1, is_past_daily_limit=True)
        self.do_permission_denied_unlock_hint_test(
            self.group1.members.first(), self.group1, self.mutation_test_suite,
            submission=submission
        )

    def test_student_unlock_hint_daily_limit_met(self) -> None:
        self.config.validate_and_update(num_hints_per_day=2)
        self.config2.validate_and_update(num_hints_per_day=1)
        # Make sure hints from other groups don't count
        self.do_unlock_hint_test(
            self.mutation_test_suite,
            self.group2,
            bugs_detected=['mut1'],
            expected_hint_number=0,
            expected_hint_text='some mut2 hint'

        )
        yesterday_submission = obj_build.make_submission(
            self.group1,
            timestamp=datetime.now(timezone.utc) - timedelta(hours=25)
        )
        yesterday_result = ag_models.MutationTestSuiteResult.objects.validate_and_create(
            mutation_test_suite=self.mutation_test_suite,
            submission=yesterday_submission,
            bugs_exposed=[]
        )
        yesterday_hint = UnlockedHint.objects.validate_and_create(
            mutation_test_suite_result=yesterday_result,
            mutation_test_suite_hint_config=self.config,
            mutant_name='mut1',
            hint_text='hint1',
            hint_number=0,
        )
        UnlockedHint.objects.filter(
            pk=yesterday_hint.pk,
        ).update(created_at=datetime.now(timezone.utc) - timedelta(hours=24, minutes=30))

        self.check_num_hints_towards_daily_limit(yesterday_result, 0, 2)

        today_result = self.do_unlock_hint_test(
            self.mutation_test_suite,
            self.group1,
            bugs_detected=['mut1'],
            expected_hint_number=0,
            expected_hint_text='some mut2 hint'
        )
        self.do_unlock_hint_test(
            self.mutation_test_suite,
            self.group1,
            result=today_result,
            expected_hint_number=1,
            expected_hint_text='other mut2 hint'
        )
        self.check_num_hints_towards_daily_limit(today_result, 2, 2)
        self.check_num_hints_towards_submission_limit(today_result, 2, None)

        self.do_bad_request_unlock_hint_test(self.group1, today_result)
        self.check_num_hints_towards_daily_limit(today_result, 2, 2)

        suite2_result = self.do_unlock_hint_test(
            self.mutation_test_suite2,
            self.group1,
            expected_hint_number=0,
            expected_hint_text='a super hint1'
        )
        self.do_bad_request_unlock_hint_test(self.group1, suite2_result)

    def test_student_unlock_hint_per_submission_limit_met(self) -> None:
        self.config.validate_and_update(num_hints_per_submission=2)
        self.config2.validate_and_update(num_hints_per_submission=1)

        # Unlock 2 hints for mutant 2 in suite 1,
        # 1 hint for mutant 1 in suite 2
        # Subsequent unlock requests are invalid because the per-submission
        # limit for each suite has been reached
        suite1_result = self.do_unlock_hint_test(
            self.mutation_test_suite,
            self.group1,
            bugs_detected=['mut1'],
            expected_hint_text='some mut2 hint',
            expected_hint_number=0,
        )
        self.check_num_hints_towards_daily_limit(suite1_result, 1, None)
        self.check_num_hints_towards_submission_limit(suite1_result, 1, 2)

        self.do_unlock_hint_test(
            self.mutation_test_suite,
            self.group1,
            result=suite1_result,
            expected_hint_text='other mut2 hint',
            expected_hint_number=1,
        )
        self.check_num_hints_towards_submission_limit(suite1_result, 2, 2)
        self.do_bad_request_unlock_hint_test(self.group1, suite1_result)

        suite2_result = self.do_unlock_hint_test(
            self.mutation_test_suite2,
            self.group1,
            submission=suite1_result.submission,
            bugs_detected=[],
            expected_hint_text='a super hint1',
            expected_hint_number=0,
        )
        self.do_bad_request_unlock_hint_test(self.group1, suite2_result)

    def test_obfuscated_mutant_names(self) -> None:
        self.fail()

    def test_project_hidden_forbidden(self) -> None:
        self.project.validate_and_update(visible_to_students=False)
        self.do_permission_denied_unlock_hint_test(
            self.group1.members.first(),
            self.group1,
            self.mutation_test_suite,
        )


@tag('slow')
class UnlockHintRaceConditionTestCase(test_ut.TransactionUnitTestBase):
    def setUp(self):
        super().setUp()
        self.client = APIClient()

        self.project = obj_build.make_project(visible_to_students=True)
        self.course = self.project.course

        self.group1 = obj_build.make_group(project=self.project)
        self.group1_submission1 = obj_build.make_finished_submission(group=self.group1)

        self.group2 = obj_build.make_group(project=self.project)
        self.group2_submission1 = obj_build.make_finished_submission(self.group2)

        self.mutation_test_suite = obj_build.make_mutation_test_suite(
            self.project,
            buggy_impl_names=['mut1', 'mut2', 'mut3_no_hints', 'mut4']
        )
        self.config = MutationTestSuiteHintConfig.objects.validate_and_create(
            mutation_test_suite=self.mutation_test_suite,
            hints_by_mutant_name={
                'mut1': ['hint1'],
                'mut2': ['some mut2 hint', 'other mut2 hint', 'more mut2 hint'],
                'mut3_no_hints': [],
            }
        )

        self.mutation_test_suite2 = obj_build.make_mutation_test_suite(
            self.project,
            buggy_impl_names=['suite2_mut1']
        )
        self.config2 = MutationTestSuiteHintConfig.objects.validate_and_create(
            mutation_test_suite=self.mutation_test_suite2,
            hints_by_mutant_name={
                'suite2_mut1': ['a super hint1'],
            }
        )

    def test_race_condition_per_submission_limit(self) -> None:
        self.config.validate_and_update(num_hints_per_submission=1)

        suite_result = ag_models.MutationTestSuiteResult.objects.validate_and_create(
            submission=self.group1_submission1,
            mutation_test_suite=self.mutation_test_suite,
            bugs_exposed=['mut1'],
        )
        user = self.group1.members.first()
        url = reverse(
            'mutation-test-suite-unlocked-hints',
            kwargs={'mutation_test_suite_result_pk': suite_result.pk}
        )

        @test_ut.sleeper_subtest('autograder.mutant_hints.views.test_ut.mocking_hook')
        def unlock_first_hint():
            client = APIClient()
            client.force_authenticate(user)
            response = client.post(url)
            self.assertEqual(status.HTTP_201_CREATED, response.status_code)
            self.assertEqual('some mut2 hint', response.data['hint_text'])
            self.assertEqual(0, response.data['hint_number'])

        subtest = unlock_first_hint()

        self.client.force_authenticate(user)
        response = self.client.post(url)
        subtest.join()
        self.assertEqual(status.HTTP_400_BAD_REQUEST, response.status_code)

    @tag('slow')
    def test_race_condition_per_day_limit(self) -> None:
        self.config.validate_and_update(num_hints_per_day=1)
        self.assertIsNone(self.config.num_hints_per_submission)
        user = self.group1.members.first()
        suite_result = ag_models.MutationTestSuiteResult.objects.validate_and_create(
            mutation_test_suite=self.mutation_test_suite,
            submission=obj_build.make_submission(self.group1),
            bugs_exposed=['mut1'],
        )
        url = reverse(
            'mutation-test-suite-unlocked-hints',
            kwargs={'mutation_test_suite_result_pk': suite_result.pk}
        )

        @test_ut.sleeper_subtest('autograder.mutant_hints.views.test_ut.mocking_hook')
        def unlock_first_hint():
            client = APIClient()
            client.force_authenticate(user)
            response = client.post(url)
            self.assertEqual(status.HTTP_201_CREATED, response.status_code)
            self.assertEqual('some mut2 hint', response.data['hint_text'])
            self.assertEqual(0, response.data['hint_number'])

        subtest = unlock_first_hint()

        self.client.force_authenticate(user)
        response = self.client.post(url)
        subtest.join()
        self.assertEqual(status.HTTP_400_BAD_REQUEST, response.status_code)


class RateHintViewTestCase(_UnlockedHintSetUp):
    def setUp(self) -> None:
        super().setUp()
        self.group1_submission1_result = ag_models.MutationTestSuiteResult.objects.validate_and_create(
            mutation_test_suite=self.mutation_test_suite,
            submission=self.group1_submission1,
            bugs_exposed=['mut1'],
        )
        self.group1_hint = UnlockedHint.objects.validate_and_create(
            mutation_test_suite_result=self.group1_submission1_result,
            mutation_test_suite_hint_config=self.config,
            mutant_name='mut2',
            hint_number=0,
            hint_text='very hint',
        )
        self.assertIsNone(self.group1_hint.hint_rating)
        self.assertEqual('', self.group1_hint.user_comment)

        self.group2_submission1_result = ag_models.MutationTestSuiteResult.objects.validate_and_create(
            mutation_test_suite=self.mutation_test_suite,
            submission=self.group2_submission1,
            bugs_exposed=[],
        )
        self.group2_hint = UnlockedHint.objects.validate_and_create(
            mutation_test_suite_result=self.group2_submission1_result,
            mutation_test_suite_hint_config=self.config,
            mutant_name='mut2',
            hint_number=0,
            hint_text='very hint',
        )
        self.assertIsNone(self.group2_hint.hint_rating)
        self.assertEqual('', self.group2_hint.user_comment)

    def get_rate_hint_url(self, hint: UnlockedHint) -> str:
        return reverse('rate-unlocked-mutant-hint', kwargs={'pk': hint.pk})

    def test_group_member_rate_hint(self) -> None:
        self.do_patch_object_test(
            self.group1_hint, self.client, self.group1.members.first(),
            self.get_rate_hint_url(self.group1_hint),
            {'hint_rating': 4}
        )

        self.do_patch_object_test(
            self.group2_hint, self.client, self.group2.members.first(),
            self.get_rate_hint_url(self.group2_hint),
            {'hint_rating': 2, 'user_comment': 'some very comment'}
        )

    def test_non_group_member_rate_hint_forbidden(self) -> None:
        self.do_patch_object_permission_denied_test(
            self.group1_hint, self.client, self.group1.members.first(),
            self.get_rate_hint_url(self.group2_hint),
            {'hint_rating': 4}
        )

    def test_hint_rating_missing(self) -> None:
        self.do_patch_object_invalid_args_test(
            self.group1_hint, self.client, self.group1.members.first(),
            self.get_rate_hint_url(self.group1_hint),
            {'user_comment': 'WAAA'}
        )

    def test_hint_rating_or_user_comment_null(self) -> None:
        self.do_patch_object_invalid_args_test(
            self.group1_hint, self.client, self.group1.members.first(),
            self.get_rate_hint_url(self.group1_hint),
            {'hint_rating': None, 'user_comment': 'WAAA'}
        )

    def test_non_editable_fields(self) -> None:
        self.do_patch_object_invalid_args_test(
            self.group1_hint, self.client, self.group1.members.first(),
            self.get_rate_hint_url(self.group1_hint),
            {'hint_rating': 2, 'hint_text': 'Weeeee'}
        )

    def test_project_hidden_forbidden(self) -> None:
        self.project.validate_and_update(visible_to_students=False)
        self.do_patch_object_permission_denied_test(
            self.group1_hint, self.client, self.group1.members.first(),
            self.get_rate_hint_url(self.group1_hint),
            {'hint_rating': 4}
        )


class HintLimitViewTestCase(_UnlockedHintSetUp):
    def test_group_member_get_limit(self) -> None:
        self.config.validate_and_update(num_hints_per_day=4, num_hints_per_submission=2)
        self.config2.validate_and_update(num_hints_per_day=3, num_hints_per_submission=1)

        submission1_result = ag_models.MutationTestSuiteResult.objects.validate_and_create(
            mutation_test_suite=self.mutation_test_suite,
            submission=obj_build.make_submission(self.group1),
            bugs_exposed=['mut1'],
        )
        self.client.force_authenticate(self.group1.members.first())
        self.client.post(self.get_result_hints_url(submission1_result))
        self.client.post(self.get_result_hints_url(submission1_result))

        submission2_result = ag_models.MutationTestSuiteResult.objects.validate_and_create(
            mutation_test_suite=self.mutation_test_suite,
            submission=obj_build.make_submission(self.group1),
            bugs_exposed=['mut1'],
        )
        self.client.post(self.get_result_hints_url(submission2_result))

        submission3_result = ag_models.MutationTestSuiteResult.objects.validate_and_create(
            mutation_test_suite=self.mutation_test_suite2,
            submission=obj_build.make_submission(self.group1),
            bugs_exposed=[],
        )
        self.client.force_authenticate(self.group1.members.first())
        self.client.post(self.get_result_hints_url(submission3_result))

        self.check_num_hints_towards_daily_limit(submission1_result, 3, 4)
        self.check_num_hints_towards_daily_limit(submission2_result, 3, 4)
        self.check_num_hints_towards_daily_limit(submission3_result, 1, 3)

        self.check_num_hints_towards_submission_limit(submission1_result, 2, 2)
        self.check_num_hints_towards_submission_limit(submission2_result, 1, 2)
        self.check_num_hints_towards_submission_limit(submission3_result, 1, 1)

    def test_staff_get_limit(self) -> None:
        self.config.validate_and_update(num_hints_per_day=2, num_hints_per_submission=1)

        result = ag_models.MutationTestSuiteResult.objects.validate_and_create(
            mutation_test_suite=self.mutation_test_suite,
            submission=obj_build.make_submission(self.group1),
            bugs_exposed=[],
        )
        self.client.force_authenticate(self.group1.members.first())
        self.client.post(self.get_result_hints_url(result))

        staff = obj_build.make_staff_user(self.course)
        self.client.force_authenticate(staff)
        self.check_num_hints_towards_daily_limit(result, 1, 2, user=staff)
        self.check_num_hints_towards_submission_limit(result, 1, 1, user=staff)

    def test_project_hidden_forbidden(self) -> None:
        self.config.validate_and_update(num_hints_per_day=2, num_hints_per_submission=1)

        result = ag_models.MutationTestSuiteResult.objects.validate_and_create(
            mutation_test_suite=self.mutation_test_suite,
            submission=obj_build.make_submission(self.group1),
            bugs_exposed=[],
        )
        self.client.force_authenticate(self.group1.members.first())
        self.client.post(self.get_result_hints_url(result))

        self.project.validate_and_update(visible_to_students=False)
        self.do_permission_denied_get_test(
            self.client, self.group1.members.first(),
            reverse(
                'mutant-hint-limits', kwargs={'mutation_test_suite_result_pk': result.pk})
        )

    def test_no_limit(self) -> None:
        result = ag_models.MutationTestSuiteResult.objects.validate_and_create(
            mutation_test_suite=self.mutation_test_suite,
            submission=obj_build.make_submission(self.group1),
            bugs_exposed=[],
        )

        self.check_num_hints_towards_daily_limit(result, 0, None)
        self.check_num_hints_towards_submission_limit(result, 0, None)


class NumMutantHintsAvailableViewTestCase(_UnlockedHintSetUp):
    def get_num_hints_remaining_url(self, result: ag_models.MutationTestSuiteResult):
        return reverse(
            'num-mutant-hints-remaining', kwargs={'mutation_test_suite_result_pk': result.pk})

    def do_num_hints_remaining_test(
        self,
        result: ag_models.MutationTestSuiteResult,
        expected_num_hints_remaining: int,
        expected_mutant_name: str,
        *,
        user: User | None = None
    ):
        if user is None:
            user = result.submission.group.members.first()

        self.client.force_authenticate(user)
        response = self.client.get(self.get_num_hints_remaining_url(result))
        self.assertEqual(status.HTTP_200_OK, response.status_code)
        self.assertEqual(expected_num_hints_remaining, response.data['num_hints_remaining'])
        self.assertEqual(expected_mutant_name, response.data['mutant_name'])

    def test_get_num_hints_remaining(self) -> None:
        submission1_result = ag_models.MutationTestSuiteResult.objects.validate_and_create(
            mutation_test_suite=self.mutation_test_suite,
            submission=obj_build.make_submission(self.group1),
            bugs_exposed=[],
        )
        self.client.force_authenticate(self.group1.members.first())
        self.do_num_hints_remaining_test(submission1_result, 1, 'mut1')
        self.client.post(self.get_result_hints_url(submission1_result))
        self.do_num_hints_remaining_test(submission1_result, 0, 'mut1')


        submission2_result = ag_models.MutationTestSuiteResult.objects.validate_and_create(
            mutation_test_suite=self.mutation_test_suite,
            submission=obj_build.make_submission(self.group1),
            bugs_exposed=['mut1'],
        )
        self.do_num_hints_remaining_test(submission2_result, 3, 'mut2')

        self.client.post(self.get_result_hints_url(submission2_result))
        self.do_num_hints_remaining_test(submission2_result, 2, 'mut2')

        self.client.post(self.get_result_hints_url(submission2_result))
        self.do_num_hints_remaining_test(submission2_result, 1, 'mut2')

        self.client.post(self.get_result_hints_url(submission2_result))
        self.do_num_hints_remaining_test(submission2_result, 0, 'mut2')

        submission3_result = ag_models.MutationTestSuiteResult.objects.validate_and_create(
            mutation_test_suite=self.mutation_test_suite,
            submission=obj_build.make_submission(self.group1),
            bugs_exposed=['mut1', 'mut2'],
        )
        self.do_num_hints_remaining_test(submission3_result, 0, 'mut3_no_hints')

    def test_staff_get_num_hints_remaining(self) -> None:
        submission1_result = ag_models.MutationTestSuiteResult.objects.validate_and_create(
            mutation_test_suite=self.mutation_test_suite,
            submission=obj_build.make_submission(self.group1),
            bugs_exposed=[],
        )
        staff = obj_build.make_staff_user(self.course)
        self.client.force_authenticate(staff)
        self.do_num_hints_remaining_test(submission1_result, 1, 'mut1', user=staff)

    def test_project_hidden_forbidden(self) -> None:
        result = ag_models.MutationTestSuiteResult.objects.validate_and_create(
            mutation_test_suite=self.mutation_test_suite,
            submission=obj_build.make_submission(self.group1),
            bugs_exposed=[],
        )
        self.project.validate_and_update(visible_to_students=False)
        self.do_permission_denied_get_test(
            self.client, self.group1.members.first(), self.get_num_hints_remaining_url(result)
        )
