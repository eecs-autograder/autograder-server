import decimal

from django.core import exceptions

from autograder.utils.testing import TransactionUnitTestBase, UnitTestBase
import autograder.core.models as ag_models
import autograder.utils.testing.model_obj_builders as obj_build


class MutationTestSuiteTestCase(UnitTestBase):
    def setUp(self):
        super().setUp()
        self.project = obj_build.make_project()
        self.name = 'qewioruqiwoeiru'

    def test_default_init(self):
        mutation_suite = ag_models.MutationTestSuite.objects.validate_and_create(
            name=self.name, project=self.project)  # type: ag_models.MutationTestSuite

        self.assertEqual(self.name, mutation_suite.name)
        self.assertEqual(self.project, mutation_suite.project)
        self.assertSequenceEqual([], mutation_suite.instructor_files_needed.all())
        self.assertTrue(mutation_suite.read_only_instructor_files)
        self.assertSequenceEqual([], mutation_suite.student_files_needed.all())
        self.assertSequenceEqual([], mutation_suite.buggy_impl_names)

        self.assertFalse(mutation_suite.use_setup_command)
        self.assertIsInstance(mutation_suite.setup_command,
                              ag_models.Command)
        self.assertIsInstance(mutation_suite.get_student_test_names_command,
                              ag_models.Command)
        self.assertEqual(ag_models.MutationTestSuite.DEFAULT_STUDENT_TEST_MAX,
                         mutation_suite.max_num_student_tests)
        self.assertEqual('any_whitespace', mutation_suite.test_name_discovery_whitespace_handling)

        self.assertIsInstance(mutation_suite.student_test_validity_check_command,
                              ag_models.Command)
        self.assertIsInstance(mutation_suite.grade_buggy_impl_command,
                              ag_models.Command)

        self.assertEqual(0, mutation_suite.points_per_exposed_bug)
        self.assertIsNone(mutation_suite.max_points)
        self.assertFalse(mutation_suite.deferred)
        self.assertEqual(ag_models.SandboxDockerImage.objects.get(name='default'),
                         mutation_suite.sandbox_docker_image)
        self.assertFalse(mutation_suite.allow_network_access)

        self.assertIsInstance(mutation_suite.normal_fdbk_config,
                              ag_models.MutationTestSuiteFeedbackConfig)
        self.assertIsInstance(mutation_suite.ultimate_submission_fdbk_config,
                              ag_models.MutationTestSuiteFeedbackConfig)
        self.assertIsInstance(mutation_suite.past_limit_submission_fdbk_config,
                              ag_models.MutationTestSuiteFeedbackConfig)
        self.assertIsInstance(mutation_suite.staff_viewer_fdbk_config,
                              ag_models.MutationTestSuiteFeedbackConfig)

        self.maxDiff = None
        ultimate_fdbk = ag_models.MutationTestSuiteFeedbackConfig.from_dict({
            'show_setup_return_code': True,
            'show_invalid_test_names': True,
            'show_points': True,
            'bugs_exposed_fdbk_level': ag_models.BugsExposedFeedbackLevel.num_bugs_exposed
        })
        self.assertEqual(ultimate_fdbk.to_dict(),
                         mutation_suite.ultimate_submission_fdbk_config.to_dict())

        low_fdbk = ag_models.MutationTestSuiteFeedbackConfig.from_dict({})
        self.assertEqual(low_fdbk.to_dict(),
                         mutation_suite.normal_fdbk_config.to_dict())

        past_limit_fdbk = mutation_suite.past_limit_submission_fdbk_config
        self.assertFalse(past_limit_fdbk.show_invalid_test_names)
        self.assertEqual(ag_models.BugsExposedFeedbackLevel.get_min(),
                         past_limit_fdbk.bugs_exposed_fdbk_level)

    def test_valid_init_non_defaults(self):
        instructor_file1 = obj_build.make_instructor_file(self.project)
        instructor_file2 = obj_build.make_instructor_file(self.project)
        student_file = obj_build.make_expected_student_file(self.project)

        sandbox_image = ag_models.SandboxDockerImage.objects.validate_and_create(
            name='such_image', display_name='An Image', tag='jameslp/imagey:2')

        values = {
            'name': 'adnlakshfdklajhsdlf',
            'project': self.project,
            'instructor_files_needed': [instructor_file1.to_dict(), instructor_file2.to_dict()],
            'read_only_instructor_files': False,
            'student_files_needed': [student_file.to_dict()],
            'buggy_impl_names': ['spam', 'egg', 'sausage', 'waaaaluigi'],
            'setup_command': {'cmd': 'g++ some_stuff.cpp'},
            'get_student_test_names_command': {'cmd': 'ls test_*.cpp'},
            'test_name_discovery_whitespace_handling': 'newline',
            'max_num_student_tests': 30,

            'student_test_validity_check_command': {
                'cmd': 'python3 validity_check.py ${student_test_name}'},
            'grade_buggy_impl_command': {
                'cmd': 'python3 grade.py ${buggy_impl_name} ${student_test_name}'
            },
            'points_per_exposed_bug': 42,
            'max_points': 462,
            'deferred': True,
            'sandbox_docker_image': sandbox_image.to_dict(),
            'allow_network_access': True,
            'normal_fdbk_config': {
                'bugs_exposed_fdbk_level': (
                    ag_models.BugsExposedFeedbackLevel.num_bugs_exposed.value),
                'show_points': True,
            },
            'ultimate_submission_fdbk_config': {
                'show_setup_stdout': True,
                'show_invalid_test_names': True,
            },
            'past_limit_submission_fdbk_config': {
                'visible': False,
                'show_setup_stderr': True,
            },
            'staff_viewer_fdbk_config': {
                'show_points': False,
            }
        }

        mutation_suite = ag_models.MutationTestSuite.objects.validate_and_create(
            **values
        )  # type: ag_models.MutationTestSuite

        self.assertCountEqual(
            [instructor_file['pk'] for instructor_file in values['instructor_files_needed']],
            [instructor_file.pk for instructor_file in
             mutation_suite.instructor_files_needed.all()])
        values.pop('instructor_files_needed')

        self.assertCountEqual(
            [student_file['pk'] for student_file in values['student_files_needed']],
            [student_file.pk for student_file in mutation_suite.student_files_needed.all()])
        values.pop('student_files_needed')

        for key, value in values.items():
            if isinstance(value, dict):
                self.assert_dict_is_subset(value, getattr(mutation_suite, key).to_dict())
            elif isinstance(value, list):
                self.assertSequenceEqual(value, getattr(mutation_suite, key))
            else:
                self.assertEqual(value, getattr(mutation_suite, key))

    def test_all_student_tests_placeholder(self) -> None:
        mutation_suite = ag_models.MutationTestSuite.objects.validate_and_create(
            name=self.name, project=self.project,
            grade_buggy_impl_command={
                'cmd': 'python3 grade.py ${buggy_impl_name} ${all_valid_test_names}'
            },
        )  # type: ag_models.MutationTestSuite

        self.assertEqual(
            'python3 grade.py ${buggy_impl_name} ${all_valid_test_names}',
            mutation_suite.grade_buggy_impl_command.cmd
        )

    def test_valid_float_points_per_exposed_bug(self):
        mutation_suite = ag_models.MutationTestSuite.objects.validate_and_create(
            name=self.name, project=self.project,
            points_per_exposed_bug='.75'
        )  # type: ag_models.MutationTestSuite

        mutation_suite.refresh_from_db()

        self.assertEqual(decimal.Decimal('.75'), mutation_suite.points_per_exposed_bug)
        self.assertEqual('0.75', mutation_suite.to_dict()['points_per_exposed_bug'])

    def test_float_points_per_exposed_bug_too_many_decimal_places(self):
        with self.assertRaises(exceptions.ValidationError) as cm:
            ag_models.MutationTestSuite.objects.validate_and_create(
                name=self.name, project=self.project,
                points_per_exposed_bug='1.123'
            )  # type: ag_models.MutationTestSuite

        self.assertIn('points_per_exposed_bug', cm.exception.message_dict)

    def test_points_per_exposed_bug_too_many_digits(self):
        with self.assertRaises(exceptions.ValidationError) as cm:
            ag_models.MutationTestSuite.objects.validate_and_create(
                name=self.name, project=self.project,
                points_per_exposed_bug='1000.123'
            )  # type: ag_models.MutationTestSuite

        self.assertIn('points_per_exposed_bug', cm.exception.message_dict)

    def test_suite_ordering(self):
        suite1 = ag_models.MutationTestSuite.objects.validate_and_create(
            name='qweiruquerw', project=self.project)
        suite2 = ag_models.MutationTestSuite.objects.validate_and_create(
            name='xjvnjadoa', project=self.project)

        self.assertCountEqual([suite1.pk, suite2.pk], self.project.get_mutationtestsuite_order())

        self.project.set_mutationtestsuite_order([suite2.pk, suite1.pk])
        self.assertSequenceEqual(
            [suite2.pk, suite1.pk], self.project.get_mutationtestsuite_order())

        self.project.set_mutationtestsuite_order([suite1.pk, suite2.pk])
        self.assertSequenceEqual(
            [suite1.pk, suite2.pk], self.project.get_mutationtestsuite_order())

    def test_error_name_not_unique(self):
        name = 'spam'
        suite1 = ag_models.MutationTestSuite.objects.validate_and_create(
            name=name, project=self.project)

        with self.assertRaises(exceptions.ValidationError):
            ag_models.MutationTestSuite.objects.validate_and_create(
                name=name, project=self.project)

    def test_max_num_student_tests_out_of_range(self):
        with self.assertRaises(exceptions.ValidationError) as cm:
            ag_models.MutationTestSuite.objects.validate_and_create(
                name=self.name, project=self.project,
                max_num_student_tests=ag_models.MutationTestSuite.MAX_STUDENT_TEST_MAX + 1)

        self.assertIn('max_num_student_tests', cm.exception.message_dict)

        with self.assertRaises(exceptions.ValidationError) as cm:
            ag_models.MutationTestSuite.objects.validate_and_create(
                name=self.name, project=self.project,
                max_num_student_tests=-1)

        self.assertIn('max_num_student_tests', cm.exception.message_dict)

    def test_validity_check_cmd_missing_placeholders(self):
        with self.assertRaises(exceptions.ValidationError) as cm:
            ag_models.MutationTestSuite.objects.validate_and_create(
                name=self.name, project=self.project,
                student_test_validity_check_command={'cmd': 'no_placeholder'})

        self.assertIn('student_test_validity_check_command', cm.exception.message_dict)

    def test_grade_buggy_impl_command_missing_placeholders(self):
        with self.assertRaises(exceptions.ValidationError) as cm:
            ag_models.MutationTestSuite.objects.validate_and_create(
                name=self.name, project=self.project,
                grade_buggy_impl_command={
                    'cmd': 'wee {}'.format(
                        ag_models.MutationTestSuite.STUDENT_TEST_NAME_PLACEHOLDER)})

        self.assertIn('grade_buggy_impl_command', cm.exception.message_dict)

        with self.assertRaises(exceptions.ValidationError) as cm:
            ag_models.MutationTestSuite.objects.validate_and_create(
                name=self.name, project=self.project,
                grade_buggy_impl_command={
                    'cmd': 'wee {}'.format(
                        ag_models.MutationTestSuite.BUGGY_IMPL_NAME_PLACEHOLDER)})

        self.assertIn('grade_buggy_impl_command', cm.exception.message_dict)

    def test_points_per_exposed_bug_out_of_range(self):
        with self.assertRaises(exceptions.ValidationError) as cm:
            ag_models.MutationTestSuite.objects.validate_and_create(
                name=self.name, project=self.project,
                points_per_exposed_bug=-1)

        self.assertIn('points_per_exposed_bug', cm.exception.message_dict)

    def test_max_points_out_of_range(self):
        with self.assertRaises(exceptions.ValidationError) as cm:
            ag_models.MutationTestSuite.objects.validate_and_create(
                name=self.name, project=self.project,
                max_points=-1)

        self.assertIn('max_points', cm.exception.message_dict)

    def test_error_instructor_file_needed_that_belongs_to_other_project(self):
        other_project = obj_build.make_project(course=self.project.course)
        other_instructor_file = obj_build.make_instructor_file(project=other_project)
        with self.assertRaises(exceptions.ValidationError) as cm:
            ag_models.MutationTestSuite.objects.validate_and_create(
                name=self.name, project=self.project,
                instructor_files_needed=[other_instructor_file.pk])

        self.assertIn('instructor_files_needed', cm.exception.message_dict)

    def test_error_student_file_needed_that_belongs_to_other_project(self):
        other_project = obj_build.make_project(course=self.project.course)
        other_student_file = obj_build.make_expected_student_file(other_project)
        with self.assertRaises(exceptions.ValidationError) as cm:
            ag_models.MutationTestSuite.objects.validate_and_create(
                name=self.name, project=self.project,
                student_files_needed=[other_student_file.pk])

        self.assertIn('student_files_needed', cm.exception.message_dict)

    def test_error_sandbox_docker_image_belongs_to_other_course(self) -> None:
        other_course = obj_build.make_course()
        other_image = obj_build.make_sandbox_docker_image(other_course)
        with self.assertRaises(exceptions.ValidationError) as cm:
            ag_models.MutationTestSuite.objects.validate_and_create(
                name=self.name, project=self.project,
                sandbox_docker_image=other_image)

        self.assertIn('sandbox_docker_image', cm.exception.message_dict)

    def test_serialization(self):
        expected_field_names = [
            'pk',
            'name',
            'project',
            'instructor_files_needed',
            'read_only_instructor_files',
            'student_files_needed',
            'buggy_impl_names',

            'use_setup_command',
            'setup_command',
            'get_student_test_names_command',
            'test_name_discovery_whitespace_handling',
            'max_num_student_tests',

            'student_test_validity_check_command',
            'grade_buggy_impl_command',
            'points_per_exposed_bug',
            'max_points',
            'deferred',
            'sandbox_docker_image',
            'allow_network_access',
            'normal_fdbk_config',
            'ultimate_submission_fdbk_config',
            'past_limit_submission_fdbk_config',
            'staff_viewer_fdbk_config',
            'last_modified',
        ]

        instructor_file = obj_build.make_instructor_file(self.project)
        student_file = obj_build.make_expected_student_file(self.project)

        mutation_suite = ag_models.MutationTestSuite.objects.validate_and_create(
            name=self.name, project=self.project,
            setup_command={'cmd': 'setuppy'},
            instructor_files_needed=[instructor_file],
            student_files_needed=[student_file]
        )  # type: ag_models.MutationTestSuite

        serialized = mutation_suite.to_dict()
        self.assertCountEqual(expected_field_names, serialized.keys())

        self.assertIsInstance(serialized['instructor_files_needed'][0], dict)
        self.assertIsInstance(serialized['student_files_needed'][0], dict)

        self.assertIsInstance(serialized['setup_command'], dict)
        self.assertIsInstance(serialized['get_student_test_names_command'], dict)
        self.assertIsInstance(serialized['student_test_validity_check_command'], dict)
        self.assertIsInstance(serialized['grade_buggy_impl_command'], dict)
        self.assertIsInstance(serialized['normal_fdbk_config'], dict)
        self.assertIsInstance(serialized['ultimate_submission_fdbk_config'], dict)
        self.assertIsInstance(serialized['past_limit_submission_fdbk_config'], dict)
        self.assertIsInstance(serialized['staff_viewer_fdbk_config'], dict)

        self.assertIsInstance(serialized['sandbox_docker_image'], dict)

        update_dict = mutation_suite.to_dict()
        non_editable = ['pk', 'project', 'last_modified']
        for field in non_editable:
            update_dict.pop(field)

        mutation_suite.validate_and_update(**update_dict)


class MutationTestSuiteSandboxImageOnDeleteTestCase(TransactionUnitTestBase):
    def test_sandbox_docker_image_set_to_default_on_delete(self):
        project = obj_build.make_project()
        sandbox_image = ag_models.SandboxDockerImage.objects.validate_and_create(
            name='waluigi', display_name='time', tag='taggy')

        suite = ag_models.MutationTestSuite.objects.validate_and_create(
            name='suiteo', project=project, sandbox_docker_image=sandbox_image
        )

        sandbox_image.delete()
        suite.refresh_from_db()
        self.assertEqual(ag_models.SandboxDockerImage.objects.get(display_name='Default'),
                         suite.sandbox_docker_image)
