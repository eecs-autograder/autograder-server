from django.core import exceptions

import autograder.core.models as ag_models
from autograder.utils.testing import UnitTestBase, generic_data


class AGTestCaseTestCase(generic_data.Project, UnitTestBase):
    def setUp(self):
        self.ag_suite = ag_models.AGTestSuite.objects.validate_and_create(
            name='suitey', project=self.project)

    def test_valid_create(self):
        name = 'ag testy'
        ag_test = ag_models.AGTestCase.objects.validate_and_create(
            name=name, ag_test_suite=self.ag_suite)

        self.assertEqual(name, ag_test.name)
        self.assertEqual(self.ag_suite, ag_test.ag_test_suite)

        self.assertTrue(ag_test.normal_fdbk_config.show_individual_commands)
        self.assertTrue(ag_test.ultimate_submission_fdbk_config.show_individual_commands)
        self.assertTrue(ag_test.past_limit_submission_fdbk_config.show_individual_commands)
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

    def test_serializable_fields(self):
        expected = [
            'pk',
            'name',
            'ag_test_suite',
        ]
        self.assertCountEqual(expected, ag_models.AGTestCase.get_serializable_fields())

    def test_editable_fields(self):
        expected = [
            'name'
        ]
        self.assertCountEqual(expected, ag_models.AGTestCase.get_editable_fields())


class AGTestCaseFeedbackConfigTestCase(UnitTestBase):
    def test_serializable_fields(self):
        expected = ['show_individual_commands']
        self.assertCountEqual(expected,
                              ag_models.AGTestCaseFeedbackConfig.get_serializable_fields())

    def test_editable_fields(self):
        expected = ['show_individual_commands']
        self.assertCountEqual(expected,
                              ag_models.AGTestCaseFeedbackConfig.get_editable_fields())
