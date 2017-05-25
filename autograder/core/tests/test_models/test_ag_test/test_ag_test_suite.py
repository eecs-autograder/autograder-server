import copy
from django.core import exceptions

import autograder.core.models as ag_models
import autograder.utils.testing.model_obj_builders as obj_build
from autograder.utils.testing import UnitTestBase


class AGTestSuiteTestCase(UnitTestBase):
    def setUp(self):
        self.project = obj_build.build_project()

    def test_valid_create_with_defaults(self):
        suite_name = 'suity'
        suite = ag_models.AGTestSuite.objects.validate_and_create(
            name=suite_name, project=self.project)

        self.assertEqual(suite_name, suite.name)
        self.assertEqual(self.project, suite.project)

        self.assertCountEqual([], suite.project_files_needed.all())
        self.assertCountEqual([], suite.student_files_needed.all())

        self.assertEqual('', suite.setup_suite_cmd)
        self.assertEqual('', suite.teardown_suite_cmd)

        self.assertFalse(suite.allow_network_access)
        self.assertFalse(suite.deferred)

        self.assertIsNotNone(suite.normal_fdbk_config)
        self.assertIsNotNone(suite.ultimate_submission_fdbk_config)
        self.assertIsNotNone(suite.past_limit_submission_fdbk_config)
        self.assertIsNotNone(suite.staff_viewer_fdbk_config)

        self.assertTrue(suite.normal_fdbk_config.show_individual_tests)
        self.assertTrue(suite.normal_fdbk_config.show_setup_and_teardown_stdout)
        self.assertTrue(suite.normal_fdbk_config.show_setup_and_teardown_stderr)

        self.assertTrue(suite.ultimate_submission_fdbk_config.show_individual_tests)
        self.assertTrue(suite.ultimate_submission_fdbk_config.show_setup_and_teardown_stdout)
        self.assertTrue(suite.ultimate_submission_fdbk_config.show_setup_and_teardown_stderr)

        self.assertTrue(suite.past_limit_submission_fdbk_config.show_individual_tests)
        self.assertTrue(suite.past_limit_submission_fdbk_config.show_setup_and_teardown_stdout)
        self.assertTrue(suite.past_limit_submission_fdbk_config.show_setup_and_teardown_stderr)

        self.assertTrue(suite.staff_viewer_fdbk_config.show_individual_tests)
        self.assertTrue(suite.staff_viewer_fdbk_config.show_setup_and_teardown_stdout)
        self.assertTrue(suite.staff_viewer_fdbk_config.show_setup_and_teardown_stderr)

    def test_valid_create_non_defaults(self):
        student_file = ag_models.ExpectedStudentFilePattern.objects.validate_and_create(
            pattern='filey',
            project=self.project)

        name = 'wee'
        project = self.project
        project_files_needed = [obj_build.make_uploaded_file(self.project)]
        student_files_needed = [student_file]
        setup_cmd = "echo 'hello world'"
        teardown_cmd = "echo 'bye'"
        allow_network_access = True
        deferred = True

        suite = ag_models.AGTestSuite.objects.validate_and_create(
            name=name,
            project=project,
            project_files_needed=project_files_needed,
            student_files_needed=student_files_needed,
            setup_suite_cmd=setup_cmd,
            teardown_suite_cmd=teardown_cmd,
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

    def test_error_project_files_and_patterns_dont_belong_to_same_project(self):
        other_project = obj_build.build_project()
        other_proj_file = obj_build.make_uploaded_file(other_project)
        other_proj_pattern = ag_models.ExpectedStudentFilePattern.objects.validate_and_create(
            pattern='alsdnvaoweijf', project=other_project)

        with self.assertRaises(exceptions.ValidationError) as cm:
            ag_models.AGTestSuite.objects.validate_and_create(
                name='aldksjfnaweij', project=self.project,
                project_files_needed=[other_proj_file],
                student_files_needed=[other_proj_pattern])

        self.assertIn('project_files_needed', cm.exception.message_dict)
        self.assertIn('student_files_needed', cm.exception.message_dict)

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

    def test_serialization(self):
        student_file = ag_models.ExpectedStudentFilePattern.objects.validate_and_create(
            pattern='filey',
            project=self.project)

        suite = ag_models.AGTestSuite.objects.validate_and_create(
            name='a;dlskfj',
            project=self.project,
            project_files_needed=[obj_build.make_uploaded_file(self.project)],
            student_files_needed=[student_file],
            setup_suite_cmd="echo 'hello world'",
            teardown_suite_cmd="echo 'bye'",
            allow_network_access=True,
            deferred=True
        )  # type: ag_models.AGTestSuite

        ag_test = ag_models.AGTestCase.objects.validate_and_create(
            name='asdfkajewfiao',
            ag_test_suite=suite
        )

        suite_dict = suite.to_dict()

        expected_keys = [
            'pk',
            'name',
            'project',

            'project_files_needed',
            'student_files_needed',

            'ag_test_cases',

            'setup_suite_cmd',
            'teardown_suite_cmd',

            'docker_image_to_use',
            'allow_network_access',
            'deferred',

            'normal_fdbk_config',
            'ultimate_submission_fdbk_config',
            'past_limit_submission_fdbk_config',
            'staff_viewer_fdbk_config',
        ]
        self.assertCountEqual(expected_keys, suite_dict.keys())

        self.assertIsInstance(suite_dict['project_files_needed'][0], dict)
        self.assertIsInstance(suite_dict['student_files_needed'][0], dict)
        self.assertSequenceEqual([ag_test.to_dict()], suite_dict['ag_test_cases'])

        self.assertIsInstance(suite_dict['normal_fdbk_config'], dict)
        self.assertIsInstance(suite_dict['ultimate_submission_fdbk_config'], dict)
        self.assertIsInstance(suite_dict['past_limit_submission_fdbk_config'], dict)
        self.assertIsInstance(suite_dict['staff_viewer_fdbk_config'], dict)

        update_dict = copy.deepcopy(suite_dict)
        for non_editable in ['pk', 'project', 'docker_image_to_use']:
            update_dict.pop(non_editable)

        suite.validate_and_update(**update_dict)
