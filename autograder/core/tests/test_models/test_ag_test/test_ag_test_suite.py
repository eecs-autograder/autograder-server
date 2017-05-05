from django.core import exceptions

import autograder.core.models as ag_models
import autograder.utils.testing.model_obj_builders as obj_build
from autograder.utils.testing import UnitTestBase, generic_data


class AGTestSuiteTestCase(generic_data.Project, UnitTestBase):
    def test_valid_create_with_defaults(self):
        suite_name = 'suity'
        suite = ag_models.AGTestSuite.objects.validate_and_create(
            name=suite_name, project=self.project)

        self.assertEqual(suite_name, suite.name)
        self.assertEqual(self.project, suite.project)

        self.assertCountEqual([], suite.project_files_needed.all())
        self.assertCountEqual([], suite.student_files_needed.all())

        self.assertFalse(suite.allow_network_access)
        self.assertFalse(suite.deferred)

        self.assertIsNotNone(suite.normal_fdbk_config)
        self.assertIsNotNone(suite.ultimate_submission_fdbk_config)
        self.assertIsNotNone(suite.past_limit_submission_fdbk_config)
        self.assertIsNotNone(suite.staff_viewer_fdbk_config)

        self.assertTrue(suite.normal_fdbk_config.show_individual_tests)
        self.assertTrue(suite.normal_fdbk_config.show_setup_command)

        self.assertTrue(suite.ultimate_submission_fdbk_config.show_individual_tests)
        self.assertTrue(suite.ultimate_submission_fdbk_config.show_setup_command)

        self.assertTrue(suite.past_limit_submission_fdbk_config.show_individual_tests)
        self.assertTrue(suite.past_limit_submission_fdbk_config.show_setup_command)

        self.assertTrue(suite.staff_viewer_fdbk_config.show_individual_tests)
        self.assertTrue(suite.staff_viewer_fdbk_config.show_setup_command)

    def test_valid_create_non_defaults(self):
        student_file = ag_models.ExpectedStudentFilePattern.objects.validate_and_create(
            pattern='filey',
            project=self.project)

        name = 'wee'
        project = self.project
        project_files_needed = [obj_build.make_uploaded_file(self.project)]
        student_files_needed = [student_file]
        allow_network_access = True
        deferred = True

        suite = ag_models.AGTestSuite.objects.validate_and_create(
            name=name,
            project=project,
            project_files_needed=project_files_needed,
            student_files_needed=student_files_needed,
            allow_network_access=allow_network_access,
            deferred=deferred,
        )

        self.assertEqual(name, suite.name)
        self.assertEqual(project, suite.project)
        self.assertCountEqual(project_files_needed, suite.project_files_needed.all())
        self.assertCountEqual(student_files_needed, suite.student_files_needed.all())
        self.assertEqual(allow_network_access, suite.allow_network_access)
        self.assertEqual(deferred, suite.deferred)

    def test_error_suite_name_not_unique(self):
        name = 'steve'
        ag_models.AGTestSuite.objects.validate_and_create(name=name, project=self.project)
        with self.assertRaises(exceptions.ValidationError):
            ag_models.AGTestSuite.objects.validate_and_create(name=name, project=self.project)

    def test_error_suite_name_empty_or_null(self):
        bad_names = ['', None]
        for name in bad_names:
            with self.assertRaises(exceptions.ValidationError) as cm:
                ag_models.AGTestSuite.objects.validate_and_create(name=name, project=self.project)

            self.assertIn('name', cm.exception.message_dict)

    def test_suite_ordering(self):
        suite1 = ag_models.AGTestSuite.objects.validate_and_create(
            name='suite1', project=self.project)
        suite2 = ag_models.AGTestSuite.objects.validate_and_create(
            name='suite2', project=self.project)

        self.assertCountEqual([suite1.pk, suite2.pk], self.project.get_agtestsuite_order())

        self.project.set_agtestsuite_order([suite1.pk, suite2.pk])
        self.assertSequenceEqual([suite1.pk, suite2.pk], self.project.get_agtestsuite_order())

        self.project.set_agtestsuite_order([suite2.pk, suite1.pk])
        self.assertSequenceEqual([suite2.pk, suite1.pk], self.project.get_agtestsuite_order())

    def test_project_suites_reverse_lookup(self):
        suite1 = ag_models.AGTestSuite.objects.validate_and_create(
            name='suite1', project=self.project)
        suite2 = ag_models.AGTestSuite.objects.validate_and_create(
            name='suite2', project=self.project)

        self.assertCountEqual([suite1, suite2], self.project.ag_test_suites.all())

    def test_serializable_fields(self):
        expected = [
            'pk',
            'name',
            'project',
            'project_files_needed',
            'student_files_needed',
            'allow_network_access',
            'deferred'
        ]

        self.assertCountEqual(expected, ag_models.AGTestSuite.get_serializable_fields())

    def test_editable_fields(self):
        expected = [
            'name',
            'project_files_needed',
            'student_files_needed',
            'allow_network_access',
            'deferred'
        ]

        self.assertCountEqual(expected, ag_models.AGTestSuite.get_editable_fields())


class AGTestSuiteFeedbackConfigTestCase(UnitTestBase):
    def test_serializable_fields(self):
        expected = [
            'pk',
            'show_individual_tests',
            'show_setup_command'
        ]

        self.assertCountEqual(expected,
                              ag_models.AGTestSuiteFeedbackConfig.get_serializable_fields())

    def test_editable_fields(self):
        expected = [
            'show_individual_tests',
            'show_setup_command'
        ]

        self.assertCountEqual(expected, ag_models.AGTestSuiteFeedbackConfig.get_editable_fields())
