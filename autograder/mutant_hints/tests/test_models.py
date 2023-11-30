import copy
import os

from django.core.exceptions import ValidationError

import autograder.core.utils as core_ut
import autograder.core.models as ag_models
from autograder.mutant_hints.models import MutationTestSuiteHintConfig, UnlockedHint
import autograder.utils.testing.model_obj_builders as obj_build
from autograder.core.models import Course, LateDaysRemaining, Semester
from autograder.core.models.course import clear_cached_user_roles
from autograder.utils.testing import UnitTestBase
import datetime


class MutationTestSuiteHintConfigTestCase(UnitTestBase):
    def setUp(self) -> None:
        super().setUp()
        self.mutation_test_suite = obj_build.make_mutation_test_suite()

    def test_valid_create_with_defaults(self) -> None:
        config = MutationTestSuiteHintConfig.objects.validate_and_create(
            mutation_test_suite=self.mutation_test_suite
        )

        self.assertEqual(self.mutation_test_suite, config.mutation_test_suite)
        self.assertEqual({}, config.hints_by_mutant_name)
        self.assertIsNone(config.num_hints_per_day)
        self.assertEqual(datetime.time(0, 0, 0, 0), config.hint_limit_reset_time)
        self.assertEqual('UTC', config.hint_limit_reset_timezone)
        self.assertIsNone(config.num_hints_per_submission)
        self.assertFalse(config.obfuscate_mutant_names)

    def test_create_no_defaults(self) -> None:
        reset_time = datetime.time(8, 42)
        config = MutationTestSuiteHintConfig.objects.validate_and_create(
            mutation_test_suite=self.mutation_test_suite,
            hints_by_mutant_name={'mutant_spam': ['hint1', 'bad hint'], 'mutant_egg': []},
            num_hints_per_day=43,
            hint_limit_reset_time=reset_time,
            hint_limit_reset_timezone='America/New_York',
            num_hints_per_submission=41,
            obfuscate_mutant_names=True,
        )

        self.assertEqual({'mutant_spam': ['hint1', 'bad hint'], 'mutant_egg': []},
                         config.hints_by_mutant_name)
        self.assertEqual(43, config.num_hints_per_day)
        self.assertEqual(reset_time, config.hint_limit_reset_time)
        self.assertEqual('America/New_York', config.hint_limit_reset_timezone)
        self.assertEqual(41, config.num_hints_per_submission)
        self.assertTrue(config.obfuscate_mutant_names)

    def test_error_num_hints_per_day_less_than_1(self) -> None:
        with self.assertRaises(ValidationError) as cm:
            MutationTestSuiteHintConfig.objects.validate_and_create(
                mutation_test_suite=self.mutation_test_suite,
                num_hints_per_day=0
            )

        self.assertIn('num_hints_per_day', cm.exception.message_dict)

        with self.assertRaises(ValidationError) as cm:
            MutationTestSuiteHintConfig.objects.validate_and_create(
                mutation_test_suite=self.mutation_test_suite,
                num_hints_per_day=-1
            )

        self.assertIn('num_hints_per_day', cm.exception.message_dict)

    def test_error_num_hints_per_submission_less_than_1(self) -> None:
        with self.assertRaises(ValidationError) as cm:
            MutationTestSuiteHintConfig.objects.validate_and_create(
                mutation_test_suite=self.mutation_test_suite,
                num_hints_per_submission=0
            )

        self.assertIn('num_hints_per_submission', cm.exception.message_dict)

        with self.assertRaises(ValidationError) as cm:
            MutationTestSuiteHintConfig.objects.validate_and_create(
                mutation_test_suite=self.mutation_test_suite,
                num_hints_per_submission=-1
            )

        self.assertIn('num_hints_per_submission', cm.exception.message_dict)

    def test_error_hints_by_mutant_name_wrong_shape(self) -> None:
        invalid_dicts = [
            {42: ['']},
            [],
            42,
            '',
            {'spam': 'egg'},
            {'spam': [42]}
        ]

        for invalid in invalid_dicts:
            with self.assertRaises(ValidationError) as cm:
                config = MutationTestSuiteHintConfig.objects.validate_and_create(
                    mutation_test_suite=self.mutation_test_suite,
                    hints_by_mutant_name=invalid,
                )
            self.assertIn('hints_by_mutant_name', cm.exception.message_dict)

    def test_serialization(self) -> None:
        config = MutationTestSuiteHintConfig.objects.validate_and_create(
            mutation_test_suite=self.mutation_test_suite
        )

        config_dict = config.to_dict()

        expected_keys = [
            'pk',
            'created_at',
            'last_modified',
            'mutation_test_suite',
            'hints_by_mutant_name',
            'num_hints_per_day',
            'hint_limit_reset_time',
            'hint_limit_reset_timezone',
            'num_hints_per_submission',
            'obfuscate_mutant_names',
        ]
        self.assertCountEqual(expected_keys, config_dict.keys())

        update_dict = copy.deepcopy(config_dict)
        non_editable = [
            'created_at',
            'last_modified',
            'mutation_test_suite',
        ]
        for field in non_editable:
            with self.assertRaises(ValidationError):
                config.validate_and_update(**{field: update_dict[field]})

            update_dict.pop(field)

        config.validate_and_update(**update_dict)


class UnlockedHintTestCase(UnitTestBase):
    def setUp(self) -> None:
        super().setUp()
        self.submission = obj_build.make_finished_submission()
        self.project = self.submission.project
        self.mutation_test_suite = obj_build.make_mutation_test_suite(self.project)
        self.config = MutationTestSuiteHintConfig.objects.validate_and_create(
            mutation_test_suite=self.mutation_test_suite
        )
        self.result = ag_models.MutationTestSuiteResult.objects.validate_and_create(
            mutation_test_suite=self.mutation_test_suite, submission=self.submission
        )


    def test_valid_create_with_defaults(self) -> None:
        hint = UnlockedHint.objects.validate_and_create(
            mutation_test_suite_result=self.result,
            mutation_test_suite_hint_config=self.config,
            mutant_name='muto1',
            hint_number=42,
            hint_text='an hint'
        )

        self.assertEqual(self.result, hint.mutation_test_suite_result)
        self.assertEqual(self.config, hint.mutation_test_suite_hint_config)
        self.assertEqual('muto1', hint.mutant_name)
        self.assertEqual(42, hint.hint_number)
        self.assertEqual('an hint', hint.hint_text)
        self.assertIsNone(hint.hint_rating)
        self.assertEqual('', hint.user_comment)

    def test_valid_create_no_defaults(self) -> None:
        hint = UnlockedHint.objects.validate_and_create(
            mutation_test_suite_result=self.result,
            mutation_test_suite_hint_config=self.config,
            mutant_name='muto2',
            hint_number=40,
            hint_text='an other hint',
            hint_rating=2,
            user_comment='some comment wow',
        )

        self.assertEqual(self.result, hint.mutation_test_suite_result)
        self.assertEqual(self.config, hint.mutation_test_suite_hint_config)
        self.assertEqual('muto2', hint.mutant_name)
        self.assertEqual(40, hint.hint_number)
        self.assertEqual('an other hint', hint.hint_text)
        self.assertEqual(2, hint.hint_rating)
        self.assertEqual('some comment wow', hint.user_comment)

    def test_serialization(self) -> None:
        hint = UnlockedHint.objects.validate_and_create(
            mutation_test_suite_result=self.result,
            mutation_test_suite_hint_config=self.config,
            mutant_name='muto2',
            hint_number=40,
            hint_text='an other hint',
            hint_rating=2,
            user_comment='some comment wow',
        )

        hint_dict = hint.to_dict()

        expected_keys = [
            'pk',
            'created_at',
            'mutation_test_suite_result',
            'mutation_test_suite_hint_config',

            'mutant_name',
            'hint_number',
            'hint_text',
            'hint_rating',
            'user_comment',
        ]
        self.assertCountEqual(expected_keys, hint_dict.keys())
