import copy

from django.core import exceptions

import autograder.core.models as ag_models
from autograder.utils.testing import UnitTestBase
import autograder.utils.testing.model_obj_builders as obj_build


class AGTestCaseTestCase(UnitTestBase):
    def setUp(self):
        super().setUp()

        self.project = obj_build.build_project()
        self.ag_suite = ag_models.AGTestSuite.objects.validate_and_create(
            name='suitey', project=self.project
        )  # type: ag_models.AGTestSuite

    def test_valid_create(self):
        name = 'ag testy'
        ag_test = ag_models.AGTestCase.objects.validate_and_create(
            name=name, ag_test_suite=self.ag_suite)

        self.assertEqual(name, ag_test.name)
        self.assertEqual(self.ag_suite, ag_test.ag_test_suite)

        self.assertTrue(ag_test.normal_fdbk_config.visible)
        self.assertTrue(ag_test.normal_fdbk_config.show_individual_commands)
        self.assertTrue(ag_test.ultimate_submission_fdbk_config.visible)
        self.assertTrue(ag_test.ultimate_submission_fdbk_config.show_individual_commands)
        self.assertTrue(ag_test.past_limit_submission_fdbk_config.visible)
        self.assertTrue(ag_test.past_limit_submission_fdbk_config.show_individual_commands)
        self.assertTrue(ag_test.staff_viewer_fdbk_config.visible)
        self.assertTrue(ag_test.staff_viewer_fdbk_config.show_individual_commands)

    def test_error_ag_test_name_not_unique(self):
        name = 'stove'
        ag_models.AGTestCase.objects.validate_and_create(name=name, ag_test_suite=self.ag_suite)
        with self.assertRaises(exceptions.ValidationError):
            ag_models.AGTestCase.objects.validate_and_create(name=name, ag_test_suite=self.ag_suite)

    def test_error_ag_test_name_empty_or_null(self):
        bad_names = ['', None]
        for name in bad_names:
            with self.assertRaises(exceptions.ValidationError) as cm:
                ag_models.AGTestCase.objects.validate_and_create(
                    name=name, ag_test_suite=self.ag_suite)

            self.assertIn('name', cm.exception.message_dict)

    def test_ag_test_ordering(self):
        ag_test1 = ag_models.AGTestCase.objects.validate_and_create(
            name='ag_test1', ag_test_suite=self.ag_suite)
        ag_test2 = ag_models.AGTestCase.objects.validate_and_create(
            name='ag_test2', ag_test_suite=self.ag_suite)

        self.assertCountEqual([ag_test1.pk, ag_test2.pk], self.ag_suite.get_agtestcase_order())

        self.ag_suite.set_agtestcase_order([ag_test2.pk, ag_test1.pk])
        self.assertSequenceEqual([ag_test2.pk, ag_test1.pk], self.ag_suite.get_agtestcase_order())

        self.ag_suite.set_agtestcase_order([ag_test1.pk, ag_test2.pk])
        self.assertSequenceEqual([ag_test1.pk, ag_test2.pk], self.ag_suite.get_agtestcase_order())

    def test_suite_ag_tests_reverse_lookup(self):
        ag_test1 = ag_models.AGTestCase.objects.validate_and_create(
            name='ag_test1', ag_test_suite=self.ag_suite)
        ag_test2 = ag_models.AGTestCase.objects.validate_and_create(
            name='ag_test2', ag_test_suite=self.ag_suite)

        self.assertCountEqual([ag_test1, ag_test2], self.ag_suite.ag_test_cases.all())

    def test_move_ag_test_to_different_suite_in_same_project(self):
        suite2 = ag_models.AGTestSuite.objects.validate_and_create(
            name='fa;weifjawef', project=self.project
        )  # type: ag_models.AGTestSuite

        ag_test = ag_models.AGTestCase.objects.validate_and_create(
            name='asdlkfjaewi;ojf', ag_test_suite=self.ag_suite
        )  # type: ag_models.AGTestCase
        cmd = ag_models.AGTestCommand.objects.validate_and_create(
            name='asdfknja;wej', ag_test_case=ag_test, cmd='asdklfja;sdjkfaldsf'
        )  # type: ag_models.AGTestCommand

        submission = obj_build.build_submission(
            submission_group=obj_build.build_submission_group(
                group_kwargs={'project': self.project}))
        suite_result = ag_models.AGTestSuiteResult.objects.validate_and_create(
            submission=submission, ag_test_suite=self.ag_suite
        )  # type: ag_models.AGTestSuiteResult
        ag_test_result = ag_models.AGTestCaseResult.objects.validate_and_create(
            ag_test_case=ag_test, ag_test_suite_result=suite_result
        )  # type: ag_models.AGTestCaseResult
        cmd_result = obj_build.make_correct_ag_test_command_result(cmd, ag_test_result)

        submission2 = obj_build.build_submission(
            submission_group=obj_build.build_submission_group(
                group_kwargs={'project': self.project}))
        suite_result2 = ag_models.AGTestSuiteResult.objects.validate_and_create(
            submission=submission2, ag_test_suite=self.ag_suite
        )  # type: ag_models.AGTestSuiteResult
        ag_test_result2 = ag_models.AGTestCaseResult.objects.validate_and_create(
            ag_test_case=ag_test, ag_test_suite_result=suite_result2
        )  # type: ag_models.AGTestCaseResult
        cmd_result2 = obj_build.make_correct_ag_test_command_result(cmd, ag_test_result2)

        self.assertEqual(self.ag_suite, ag_test.ag_test_suite)

        # This that should be re-wired after this line:
        # - ag_test should belong to suite2
        # - Any AGTestSuiteResults that belonged to self.ag_suite should belong
        #   to suite2.
        ag_test.validate_and_update(ag_test_suite=suite2)

        suite2 = ag_models.AGTestSuite.objects.get(pk=suite2.pk)
        self.assertSequenceEqual([ag_test], suite2.ag_test_cases.all())

        self.ag_suite.refresh_from_db()
        self.assertSequenceEqual([], self.ag_suite.ag_test_cases.all())

        ag_test_result = ag_models.AGTestCaseResult.objects.get(pk=ag_test_result.pk)
        self.assertEqual(suite2, ag_test_result.ag_test_suite_result.ag_test_suite)
        ag_test_result2 = ag_models.AGTestCaseResult.objects.get(pk=ag_test_result2.pk)
        self.assertEqual(suite2, ag_test_result2.ag_test_suite_result.ag_test_suite)

        self.assertEqual(ag_test_result, cmd_result.ag_test_case_result)
        self.assertEqual(ag_test_result2, cmd_result2.ag_test_case_result)

    def test_error_move_ag_test_to_suite_in_different_project(self):
        ag_test = ag_models.AGTestCase.objects.validate_and_create(
            name='asdlkfjaewi;ojf', ag_test_suite=self.ag_suite
        )  # type: ag_models.AGTestCase

        project2 = obj_build.build_project()
        suite2 = ag_models.AGTestSuite.objects.validate_and_create(
            name='fa;weifjawef', project=project2)  # type: ag_models.AGTestSuite

        with self.assertRaises(exceptions.ValidationError) as cm:
            ag_test.validate_and_update(ag_test_suite=suite2)

        self.assertIn('ag_test_suite', cm.exception.message_dict)

    def test_serialize(self):
        ag_test = ag_models.AGTestCase.objects.validate_and_create(
            name='a;sdklfjsdas;dkf', ag_test_suite=self.ag_suite)  # type: ag_models.AGTestCase
        cmd = obj_build.make_full_ag_test_command(ag_test)

        test_dict = ag_test.to_dict()

        expected_keys = [
            'pk',
            'name',
            'ag_test_suite',
            'ag_test_commands',
            'normal_fdbk_config',
            'ultimate_submission_fdbk_config',
            'past_limit_submission_fdbk_config',
            'staff_viewer_fdbk_config',
        ]

        self.assertCountEqual(expected_keys, test_dict.keys())

        self.assertSequenceEqual([cmd.to_dict()], test_dict['ag_test_commands'])

        self.assertIsInstance(test_dict['normal_fdbk_config'], dict)
        self.assertIsInstance(test_dict['ultimate_submission_fdbk_config'], dict)
        self.assertIsInstance(test_dict['past_limit_submission_fdbk_config'], dict)
        self.assertIsInstance(test_dict['staff_viewer_fdbk_config'], dict)

        update_dict = copy.deepcopy(test_dict)
        update_dict.pop('pk')
        update_dict.pop('ag_test_commands')
        ag_test.validate_and_update(**update_dict)
