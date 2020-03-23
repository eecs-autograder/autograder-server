import copy

from django.core import exceptions
from django.db import IntegrityError

import autograder.core.models as ag_models
import autograder.utils.testing.model_obj_builders as obj_build
from autograder.core import constants
from autograder.utils.testing import TransactionUnitTestBase, UnitTestBase


class AGTestSuiteTestCase(UnitTestBase):
    def setUp(self):
        super().setUp()
        self.project = obj_build.build_project()

    def test_valid_create_with_defaults(self):
        suite_name = 'suity'
        suite = ag_models.AGTestSuite.objects.validate_and_create(
            name=suite_name, project=self.project)

        self.assertEqual(suite_name, suite.name)
        self.assertEqual(self.project, suite.project)

        self.assertCountEqual([], suite.instructor_files_needed.all())
        self.assertTrue(suite.read_only_instructor_files)
        self.assertCountEqual([], suite.student_files_needed.all())

        self.assertEqual('', suite.setup_suite_cmd_name)
        self.assertEqual('', suite.setup_suite_cmd)

        self.assertFalse(suite.allow_network_access)
        self.assertEqual(ag_models.SandboxDockerImage.objects.get(name='default'),
                         suite.sandbox_docker_image)
        self.assertFalse(suite.deferred)

        self.assertIsNotNone(suite.normal_fdbk_config)
        self.assertIsNotNone(suite.ultimate_submission_fdbk_config)
        self.assertIsNotNone(suite.past_limit_submission_fdbk_config)
        self.assertIsNotNone(suite.staff_viewer_fdbk_config)

        self.assertTrue(suite.normal_fdbk_config.visible)
        self.assertTrue(suite.normal_fdbk_config.show_individual_tests)
        self.assertTrue(suite.normal_fdbk_config.show_setup_return_code)
        self.assertTrue(suite.normal_fdbk_config.show_setup_timed_out)
        self.assertTrue(suite.normal_fdbk_config.show_setup_stdout)
        self.assertTrue(suite.normal_fdbk_config.show_setup_stderr)

        self.assertTrue(suite.ultimate_submission_fdbk_config.visible)
        self.assertTrue(suite.ultimate_submission_fdbk_config.show_individual_tests)
        self.assertTrue(suite.ultimate_submission_fdbk_config.show_setup_return_code)
        self.assertTrue(suite.ultimate_submission_fdbk_config.show_setup_timed_out)
        self.assertTrue(suite.ultimate_submission_fdbk_config.show_setup_stdout)
        self.assertTrue(suite.ultimate_submission_fdbk_config.show_setup_stderr)

        self.assertTrue(suite.past_limit_submission_fdbk_config.visible)
        self.assertTrue(suite.past_limit_submission_fdbk_config.show_individual_tests)
        self.assertTrue(
            suite.past_limit_submission_fdbk_config.show_setup_return_code)
        self.assertTrue(suite.past_limit_submission_fdbk_config.show_setup_timed_out)
        self.assertTrue(suite.past_limit_submission_fdbk_config.show_setup_stdout)
        self.assertTrue(suite.past_limit_submission_fdbk_config.show_setup_stderr)

        self.assertTrue(suite.staff_viewer_fdbk_config.visible)
        self.assertTrue(suite.staff_viewer_fdbk_config.show_individual_tests)
        self.assertTrue(suite.staff_viewer_fdbk_config.show_setup_return_code)
        self.assertTrue(suite.staff_viewer_fdbk_config.show_setup_timed_out)
        self.assertTrue(suite.staff_viewer_fdbk_config.show_setup_stdout)
        self.assertTrue(suite.staff_viewer_fdbk_config.show_setup_stderr)

    def test_valid_create_non_defaults(self):
        student_file = ag_models.ExpectedStudentFile.objects.validate_and_create(
            pattern='filey',
            project=self.project)

        name = 'wee'
        project = self.project
        instructor_files_needed = [obj_build.make_instructor_file(self.project)]
        student_files_needed = [student_file]
        setup_cmd = "echo 'hello world'"
        allow_network_access = True
        deferred = True

        sandbox_image = ag_models.SandboxDockerImage.objects.validate_and_create(
            name='image', display_name='An Image', tag='jameslp/imagey:1')

        suite = ag_models.AGTestSuite.objects.validate_and_create(
            name=name,
            project=project,
            instructor_files_needed=instructor_files_needed,
            read_only_instructor_files=False,
            student_files_needed=student_files_needed,
            setup_suite_cmd=setup_cmd,
            setup_suite_cmd_name='steve',
            allow_network_access=allow_network_access,
            deferred=deferred,
            sandbox_docker_image=sandbox_image.to_dict(),
            normal_fdbk_config={
                'visible': False,
                'show_individual_tests': False,
                'show_setup_return_code': False,
                'show_setup_timed_out': False,
                'show_setup_stdout': False,
                'show_setup_stderr': False,
            }
        )

        suite.refresh_from_db()
        self.assertEqual(name, suite.name)
        self.assertEqual(project, suite.project)
        self.assertCountEqual(instructor_files_needed, suite.instructor_files_needed.all())
        self.assertFalse(suite.read_only_instructor_files)
        self.assertCountEqual(student_files_needed, suite.student_files_needed.all())
        self.assertEqual(allow_network_access, suite.allow_network_access)
        self.assertEqual(deferred, suite.deferred)
        self.assertEqual(sandbox_image, suite.sandbox_docker_image)
        self.assertFalse(suite.normal_fdbk_config.visible)

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

    def test_error_instructor_and_student_files_dont_belong_to_same_project(self):
        other_project = obj_build.build_project()
        other_instructor_file = obj_build.make_instructor_file(other_project)
        other_student_file = ag_models.ExpectedStudentFile.objects.validate_and_create(
            pattern='alsdnvaoweijf', project=other_project)

        with self.assertRaises(exceptions.ValidationError) as cm:
            ag_models.AGTestSuite.objects.validate_and_create(
                name='aldksjfnaweij', project=self.project,
                instructor_files_needed=[other_instructor_file],
                student_files_needed=[other_student_file])

        self.assertIn('instructor_files_needed', cm.exception.message_dict)
        self.assertIn('student_files_needed', cm.exception.message_dict)

    def test_error_sandbox_docker_image_belongs_to_other_course(self) -> None:
        other_course = obj_build.make_course()
        other_image = obj_build.make_sandbox_docker_image(other_course)
        with self.assertRaises(exceptions.ValidationError) as cm:
            ag_models.AGTestSuite.objects.validate_and_create(
                name='An suite', project=self.project,
                sandbox_docker_image=other_image)

        self.assertIn('sandbox_docker_image', cm.exception.message_dict)

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
        student_file = ag_models.ExpectedStudentFile.objects.validate_and_create(
            pattern='filey',
            project=self.project)

        suite = ag_models.AGTestSuite.objects.validate_and_create(
            name='a;dlskfj',
            project=self.project,
            instructor_files_needed=[obj_build.make_instructor_file(self.project)],
            student_files_needed=[student_file],
            setup_suite_cmd="echo 'hello world'",
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
            'last_modified',

            'instructor_files_needed',
            'read_only_instructor_files',
            'student_files_needed',

            'ag_test_cases',

            'setup_suite_cmd',
            'setup_suite_cmd_name',

            'sandbox_docker_image',
            'allow_network_access',
            'deferred',

            'normal_fdbk_config',
            'ultimate_submission_fdbk_config',
            'past_limit_submission_fdbk_config',
            'staff_viewer_fdbk_config',
        ]
        self.assertCountEqual(expected_keys, suite_dict.keys())

        self.assertIsInstance(suite_dict['instructor_files_needed'][0], dict)
        self.assertIsInstance(suite_dict['student_files_needed'][0], dict)
        self.assertSequenceEqual([ag_test.to_dict()], suite_dict['ag_test_cases'])
        self.assertIsInstance(suite_dict['sandbox_docker_image'], dict)

        self.assertIsInstance(suite_dict['normal_fdbk_config'], dict)
        self.assertIsInstance(suite_dict['ultimate_submission_fdbk_config'], dict)
        self.assertIsInstance(suite_dict['past_limit_submission_fdbk_config'], dict)
        self.assertIsInstance(suite_dict['staff_viewer_fdbk_config'], dict)

        update_dict = copy.deepcopy(suite_dict)
        for non_editable in ['pk', 'project', 'last_modified',
                             'ag_test_cases']:
            update_dict.pop(non_editable)

        suite.validate_and_update(**update_dict)


class AGTestSuiteSandboxImageOnDeleteTestCase(TransactionUnitTestBase):
    def test_sandbox_docker_image_set_to_default_on_delete(self):
        project = obj_build.make_project()
        sandbox_image = ag_models.SandboxDockerImage.objects.validate_and_create(
            name='waaaa', display_name='luigi', tag='taggy')

        suite = ag_models.AGTestSuite.objects.validate_and_create(
            name='suiteo', project=project, sandbox_docker_image=sandbox_image
        )

        sandbox_image.delete()
        suite.refresh_from_db()
        self.assertEqual(ag_models.SandboxDockerImage.objects.get(display_name='Default'),
                         suite.sandbox_docker_image)
