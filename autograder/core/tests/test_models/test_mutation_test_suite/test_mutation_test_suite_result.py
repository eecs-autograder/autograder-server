import decimal
import os

import autograder.core.models as ag_models
from autograder.core.submission_feedback import MutationTestSuitePreLoader
from autograder.utils.testing import UnitTestBase
import autograder.utils.testing.model_obj_builders as obj_build
import autograder.core.utils as core_ut


class MutationTestSuiteResultTestCase(UnitTestBase):
    def setUp(self):
        super().setUp()
        self.submission = obj_build.make_submission()
        self.project = self.submission.group.project
        self.mutation_suite = ag_models.MutationTestSuite.objects.validate_and_create(
            name='qewirqwekljr', project=self.project)

    def test_default_init(self):
        result = ag_models.MutationTestSuiteResult.objects.validate_and_create(
            mutation_test_suite=self.mutation_suite, submission=self.submission
        )  # type: ag_models.MutationTestSuiteResult

        self.assertEqual(self.mutation_suite, result.mutation_test_suite)
        self.assertEqual(self.submission, result.submission)
        self.assertSequenceEqual([], result.student_tests)
        self.assertSequenceEqual([], result.discarded_tests)
        self.assertSequenceEqual([], result.invalid_tests)
        self.assertSequenceEqual([], result.timed_out_tests)
        self.assertSequenceEqual([], result.bugs_exposed)
        self.assertIsNone(result.setup_result)
        self.assertIsInstance(result.get_test_names_result, ag_models.AGCommandResult)

    def test_output_filenames(self):
        result = ag_models.MutationTestSuiteResult.objects.validate_and_create(
            mutation_test_suite=self.mutation_suite, submission=self.submission)

        self.assertEqual(
            os.path.join(core_ut.get_result_output_dir(self.submission),
                         'student_suite_result_{}_validity_check_stdout'.format(result.pk)),
            result.validity_check_stdout_filename)
        self.assertEqual(
            os.path.join(core_ut.get_result_output_dir(self.submission),
                         'student_suite_result_{}_validity_check_stderr'.format(result.pk)),
            result.validity_check_stderr_filename)
        self.assertEqual(
            os.path.join(core_ut.get_result_output_dir(self.submission),
                         'student_suite_result_{}_grade_buggy_impls_stdout'.format(result.pk)),
            result.grade_buggy_impls_stdout_filename)
        self.assertEqual(
            os.path.join(core_ut.get_result_output_dir(self.submission),
                         'student_suite_result_{}_grade_buggy_impls_stderr'.format(result.pk)),
            result.grade_buggy_impls_stderr_filename)


class MutationTestSuiteResultFeedbackTestCase(UnitTestBase):
    def setUp(self):
        super().setUp()
        self.submission = obj_build.make_submission()
        self.project = self.submission.group.project

        self.bug_names = ['bug{}'.format(i) for i in range(5)]
        self.points_per_exposed_bug = decimal.Decimal('2.5')
        self.points_possible = len(self.bug_names) * self.points_per_exposed_bug

        self.mutation_suite = ag_models.MutationTestSuite.objects.validate_and_create(
            name='adnfa;kdsfj', project=self.project,
            buggy_impl_names=self.bug_names,

            use_setup_command=True,
            setup_command={
                'cmd': 'echo waaaluigi',
            },
            points_per_exposed_bug=self.points_per_exposed_bug,
        )  # type: ag_models.MutationTestSuite

        self.setup_stdout = 'adskfja;nrstslekjaf'
        self.setup_stderr = 'amnak;sdjvaie'
        self.validity_check_stdout = 'aasdf'
        self.validity_check_stderr = 'lknrstjll'
        self.grade_buggy_impls_stdout = 'aoenrstnrtsnwij'
        self.grade_buggy_impls_stderr = 'cvasdop;f'

        self.setup_result = ag_models.AGCommandResult.objects.validate_and_create(
            return_code=0
        )  # type: ag_models.AGCommandResult

        with open(self.setup_result.stdout_filename, 'w') as f:
            f.write(self.setup_stdout)
        with open(self.setup_result.stderr_filename, 'w') as f:
            f.write(self.setup_stderr)

        self.valid_tests = ['test{}'.format(i) for i in range(3)]
        self.invalid_tests = ['bad{}'.format(i) for i in range(4)]
        self.timeout_tests = ['not_sanic{}'.format(i) for i in range(2)]

        self.student_tests = self.valid_tests + self.invalid_tests + self.timeout_tests
        self.get_test_names_stdout = ''.join(self.student_tests)
        self.get_test_names_stderr = 'did some things'

        self.get_test_names_return_code = 47
        self.get_test_names_result = ag_models.AGCommandResult.objects.validate_and_create(
            return_code=self.get_test_names_return_code
        )  # type: ag_models.AGCommandResult
        with open(self.get_test_names_result.stdout_filename, 'w') as f:
            f.write(self.get_test_names_stdout)
        with open(self.get_test_names_result.stderr_filename, 'w') as f:
            f.write(self.get_test_names_stderr)

        self.bugs_exposed = self.bug_names
        self.points_awarded = len(self.bugs_exposed) * self.points_per_exposed_bug

        self.result = ag_models.MutationTestSuiteResult.objects.validate_and_create(
            mutation_test_suite=self.mutation_suite, submission=self.submission,
            student_tests=self.student_tests,
            invalid_tests=self.invalid_tests,
            timed_out_tests=self.timeout_tests,
            bugs_exposed=self.bugs_exposed,
            setup_result=self.setup_result,
            get_test_names_result=self.get_test_names_result
        )  # type: ag_models.MutationTestSuiteResult

        with open(self.result.validity_check_stdout_filename, 'w') as f:
            f.write(self.validity_check_stdout)
        with open(self.result.validity_check_stderr_filename, 'w') as f:
            f.write(self.validity_check_stderr)
        with open(self.result.grade_buggy_impls_stdout_filename, 'w') as f:
            f.write(self.grade_buggy_impls_stdout)
        with open(self.result.grade_buggy_impls_stderr_filename, 'w') as f:
            f.write(self.grade_buggy_impls_stderr)

    def test_feedback_calculator_factory_method(self):
        self.assertEqual(
            self.mutation_suite.normal_fdbk_config.to_dict(),
            self.result.get_fdbk(
                ag_models.FeedbackCategory.normal,
                MutationTestSuitePreLoader(self.project)).fdbk_settings)
        self.assertEqual(
            self.mutation_suite.ultimate_submission_fdbk_config.to_dict(),
            self.result.get_fdbk(
                ag_models.FeedbackCategory.ultimate_submission,
                MutationTestSuitePreLoader(self.project)).fdbk_settings)
        self.assertEqual(
            self.mutation_suite.past_limit_submission_fdbk_config.to_dict(),
            self.result.get_fdbk(
                ag_models.FeedbackCategory.past_limit_submission,
                MutationTestSuitePreLoader(self.project)).fdbk_settings)
        self.assertEqual(
            self.mutation_suite.staff_viewer_fdbk_config.to_dict(),
            self.result.get_fdbk(
                ag_models.FeedbackCategory.staff_viewer,
                MutationTestSuitePreLoader(self.project)).fdbk_settings)

        max_fdbk = self.result.get_fdbk(
            ag_models.FeedbackCategory.max,
            MutationTestSuitePreLoader(self.project)).fdbk_conf
        self.assertTrue(max_fdbk.visible)
        self.assertTrue(max_fdbk.show_setup_return_code)
        self.assertTrue(max_fdbk.show_setup_stdout)
        self.assertTrue(max_fdbk.show_setup_stderr)
        self.assertTrue(max_fdbk.show_validity_check_stdout)
        self.assertTrue(max_fdbk.show_validity_check_stderr)
        self.assertTrue(max_fdbk.show_grade_buggy_impls_stdout)
        self.assertTrue(max_fdbk.show_grade_buggy_impls_stderr)
        self.assertTrue(max_fdbk.show_invalid_test_names)
        self.assertTrue(max_fdbk.show_points)
        self.assertEqual(ag_models.BugsExposedFeedbackLevel.get_max(),
                         max_fdbk.bugs_exposed_fdbk_level)

    def test_discarded_tests(self):
        discarded_tests = ['spam', 'egg']
        self.result.discarded_tests = discarded_tests
        fdbk = self.result.get_fdbk(
            ag_models.FeedbackCategory.normal,
            MutationTestSuitePreLoader(self.project))
        self.assertSequenceEqual(discarded_tests, fdbk.discarded_tests)

    def test_points_values_catch_all_bugs(self):
        fdbk = self.result.get_fdbk(
            ag_models.FeedbackCategory.max,
            MutationTestSuitePreLoader(self.project))
        self.assertEqual(self.points_awarded, fdbk.total_points)
        self.assertEqual(self.points_possible, fdbk.total_points_possible)

    def test_points_values_catch_some_bugs(self):
        num_bugs_exposed = len(self.bug_names) // 2
        self.assertGreater(num_bugs_exposed, 0)
        self.result.bugs_exposed = self.bug_names[:num_bugs_exposed]
        self.result.save()

        fdbk = self.result.get_fdbk(
            ag_models.FeedbackCategory.max,
            MutationTestSuitePreLoader(self.project))
        self.assertEqual(num_bugs_exposed * self.points_per_exposed_bug, fdbk.total_points)
        self.assertEqual(self.points_possible, fdbk.total_points_possible)

    def test_points_values_catch_no_bugs(self):
        self.result.bugs_exposed = []
        self.result.save()

        fdbk = self.result.get_fdbk(
            ag_models.FeedbackCategory.max,
            MutationTestSuitePreLoader(self.project))
        self.assertEqual(0, fdbk.total_points)
        self.assertEqual(self.points_possible, fdbk.total_points_possible)

    def test_points_values_with_max_points_set_catch_all_bugs(self):
        max_points = self.points_possible // 2
        self.assertGreater(max_points, 0)
        self.mutation_suite.validate_and_update(max_points=max_points)

        fdbk = self.result.get_fdbk(
            ag_models.FeedbackCategory.max,
            MutationTestSuitePreLoader(self.project))
        self.assertEqual(max_points, fdbk.total_points)
        self.assertEqual(max_points, fdbk.total_points_possible)

    def test_points_values_with_max_points_set_catch_no_bugs(self):
        max_points = self.points_possible // 2
        self.assertGreater(max_points, 0)
        self.mutation_suite.validate_and_update(max_points=max_points)

        self.result.bugs_exposed = []
        self.result.save()

        fdbk = self.result.get_fdbk(
            ag_models.FeedbackCategory.max,
            MutationTestSuitePreLoader(self.project))
        self.assertEqual(0, fdbk.total_points)
        self.assertEqual(max_points, fdbk.total_points_possible)

    def test_setup_command_name(self):
        name = 'wuuuuuuuluigio42'
        self.mutation_suite.validate_and_update(setup_command={'name': name})

        fdbk = self.result.get_fdbk(
            ag_models.FeedbackCategory.normal,
            MutationTestSuitePreLoader(self.project))
        self.assertEqual(name, fdbk.setup_command_name)

    def test_has_setup_command(self):
        fdbk = self.result.get_fdbk(
            ag_models.FeedbackCategory.normal,
            MutationTestSuitePreLoader(self.project))
        self.assertTrue(fdbk.has_setup_command)

    def test_show_and_hide_setup_return_code(self):
        self.mutation_suite.validate_and_update(
            normal_fdbk_config={'show_setup_return_code': True})

        return_code = 31
        self.result.setup_result.return_code = return_code
        self.setup_result.save()
        fdbk = self.result.get_fdbk(
            ag_models.FeedbackCategory.normal,
            MutationTestSuitePreLoader(self.project))
        self.assertEqual(return_code, fdbk.setup_return_code)
        self.assertIsNotNone(fdbk.setup_timed_out)
        self.assertFalse(fdbk.setup_timed_out)

        self.mutation_suite.validate_and_update(
            normal_fdbk_config={'show_setup_return_code': False})

        fdbk = self.result.get_fdbk(
            ag_models.FeedbackCategory.normal,
            MutationTestSuitePreLoader(self.project))
        self.assertIsNone(fdbk.setup_return_code)
        self.assertIsNone(fdbk.setup_timed_out)

    def test_show_setup_return_code_return_code_is_none_timed_out_is_true(self):
        """
        This is a regression test for:
            https://github.com/eecs-autograder/autograder-server/issues/385
        """
        self.mutation_suite.validate_and_update(
            normal_fdbk_config={'show_setup_return_code': True})

        self.result.setup_result.return_code = None
        self.result.setup_result.timed_out = True
        self.setup_result.save()
        fdbk = self.result.get_fdbk(
            ag_models.FeedbackCategory.normal,
            MutationTestSuitePreLoader(self.project))
        self.assertIsNone(fdbk.setup_return_code)
        self.assertIsNotNone(fdbk.setup_timed_out)
        self.assertTrue(fdbk.setup_timed_out)

    def test_show_setup_return_code_with_setup_result_but_no_setup_cmd(self):
        self.mutation_suite.validate_and_update(use_setup_command=False)
        self.mutation_suite.validate_and_update(
            normal_fdbk_config={'show_setup_return_code': True})

        fdbk = self.result.get_fdbk(
            ag_models.FeedbackCategory.normal,
            MutationTestSuitePreLoader(self.project))
        self.assertIsNotNone(self.result.setup_result.return_code)
        self.assertEqual(self.result.setup_result.return_code, fdbk.setup_return_code)

        self.assertIsNotNone(self.result.setup_result.timed_out)
        self.assertEqual(self.result.setup_result.timed_out, fdbk.setup_timed_out)

    def test_show_setup_return_code_with_setup_cmd_but_no_setup_result(self):
        self.assertIsNotNone(self.mutation_suite.setup_command)
        self.mutation_suite.validate_and_update(
            normal_fdbk_config={'show_setup_return_code': True})

        self.result.setup_result = None
        self.result.save()
        fdbk = self.result.get_fdbk(
            ag_models.FeedbackCategory.normal,
            MutationTestSuitePreLoader(self.project))
        self.assertIsNone(fdbk.setup_return_code)
        self.assertIsNone(fdbk.setup_timed_out)

    def test_show_and_hide_setup_stdout(self):
        self.mutation_suite.validate_and_update(normal_fdbk_config={'show_setup_stdout': True})
        fdbk = self.result.get_fdbk(
            ag_models.FeedbackCategory.normal,
            MutationTestSuitePreLoader(self.project))
        self.assertEqual(self.setup_stdout, fdbk.setup_stdout.read().decode())
        self.assertEqual(len(self.setup_stdout), fdbk.get_setup_stdout_size())

        self.mutation_suite.validate_and_update(normal_fdbk_config={'show_setup_stdout': False})
        fdbk = self.result.get_fdbk(
            ag_models.FeedbackCategory.normal,
            MutationTestSuitePreLoader(self.project))
        self.assertIsNone(fdbk.setup_stdout)
        self.assertIsNone(fdbk.get_setup_stdout_size())

    def test_show_and_hide_setup_stderr(self):
        self.mutation_suite.validate_and_update(normal_fdbk_config={'show_setup_stderr': True})
        fdbk = self.result.get_fdbk(
            ag_models.FeedbackCategory.normal,
            MutationTestSuitePreLoader(self.project))
        self.assertEqual(self.setup_stderr, fdbk.setup_stderr.read().decode())
        self.assertEqual(len(self.setup_stderr), fdbk.get_setup_stderr_size())

        self.mutation_suite.validate_and_update(normal_fdbk_config={'show_setup_stderr': False})
        fdbk = self.result.get_fdbk(
            ag_models.FeedbackCategory.normal,
            MutationTestSuitePreLoader(self.project))
        self.assertIsNone(fdbk.setup_stderr)
        self.assertIsNone(fdbk.get_setup_stderr_size())

    def test_show_setup_stdout_and_stderr_with_setup_result_but_no_setup_cmd(self):
        self.mutation_suite.validate_and_update(use_setup_command=False)
        self.mutation_suite.validate_and_update(
            normal_fdbk_config={'show_setup_stdout': True, 'show_setup_stderr': True})
        fdbk = self.result.get_fdbk(
            ag_models.FeedbackCategory.normal,
            MutationTestSuitePreLoader(self.project))
        self.assertEqual(self.setup_stdout, fdbk.setup_stdout.read().decode())
        self.assertEqual(len(self.setup_stdout), fdbk.get_setup_stdout_size())
        self.assertEqual(self.setup_stderr, fdbk.setup_stderr.read().decode())
        self.assertEqual(len(self.setup_stderr), fdbk.get_setup_stderr_size())

    def test_show_setup_stdout_and_stderr_with_setup_cmd_but_no_setup_result(self):
        self.assertIsNotNone(self.mutation_suite.setup_command)
        self.mutation_suite.validate_and_update(
            normal_fdbk_config={'show_setup_stdout': True, 'show_setup_stderr': True})

        self.result.setup_result = None
        self.result.save()
        fdbk = self.result.get_fdbk(
            ag_models.FeedbackCategory.normal,
            MutationTestSuitePreLoader(self.project))
        self.assertIsNone(fdbk.setup_stdout)
        self.assertIsNone(fdbk.get_setup_stderr_size())
        self.assertIsNone(fdbk.setup_stderr)
        self.assertIsNone(fdbk.get_setup_stderr_size())

    def test_show_and_hide_get_test_names_return_code(self):
        self.mutation_suite.validate_and_update(
            normal_fdbk_config={'show_get_test_names_return_code': True})

        fdbk = self.result.get_fdbk(
            ag_models.FeedbackCategory.normal,
            MutationTestSuitePreLoader(self.project))
        self.assertEqual(self.get_test_names_return_code, fdbk.get_student_test_names_return_code)
        self.assertIsNotNone(fdbk.get_student_test_names_timed_out)
        self.assertFalse(fdbk.get_student_test_names_timed_out)

        self.mutation_suite.validate_and_update(
            normal_fdbk_config={'show_get_test_names_return_code': False})

        fdbk = self.result.get_fdbk(
            ag_models.FeedbackCategory.normal,
            MutationTestSuitePreLoader(self.project))
        self.assertIsNone(fdbk.get_student_test_names_return_code)
        self.assertIsNone(fdbk.get_student_test_names_timed_out)

    def test_show_and_hide_get_test_names_stdout(self):
        self.mutation_suite.validate_and_update(
            normal_fdbk_config={'show_get_test_names_stdout': True})
        fdbk = self.result.get_fdbk(
            ag_models.FeedbackCategory.normal,
            MutationTestSuitePreLoader(self.project))
        self.assertEqual(self.get_test_names_stdout,
                         fdbk.get_student_test_names_stdout.read().decode())
        self.assertEqual(len(self.get_test_names_stdout),
                         fdbk.get_student_test_names_stdout_size())

        self.mutation_suite.validate_and_update(
            normal_fdbk_config={'show_get_test_names_stdout': False})
        fdbk = self.result.get_fdbk(
            ag_models.FeedbackCategory.normal,
            MutationTestSuitePreLoader(self.project))
        self.assertIsNone(fdbk.get_student_test_names_stdout)
        self.assertIsNone(fdbk.get_student_test_names_stdout_size())

    def test_show_and_hide_get_test_names_stderr(self):
        self.mutation_suite.validate_and_update(
            normal_fdbk_config={'show_get_test_names_stderr': True})
        fdbk = self.result.get_fdbk(
            ag_models.FeedbackCategory.normal,
            MutationTestSuitePreLoader(self.project))
        self.assertEqual(self.get_test_names_stderr,
                         fdbk.get_student_test_names_stderr.read().decode())
        self.assertEqual(len(self.get_test_names_stderr),
                         fdbk.get_student_test_names_stderr_size())

        self.mutation_suite.validate_and_update(
            normal_fdbk_config={'show_get_test_names_stderr': False})
        fdbk = self.result.get_fdbk(
            ag_models.FeedbackCategory.normal,
            MutationTestSuitePreLoader(self.project))
        self.assertIsNone(fdbk.get_student_test_names_stderr)
        self.assertIsNone(fdbk.get_student_test_names_stderr_size())

    def test_show_and_hide_validity_check_stdout(self):
        self.mutation_suite.validate_and_update(
            normal_fdbk_config={'show_validity_check_stdout': True})
        fdbk = self.result.get_fdbk(
            ag_models.FeedbackCategory.normal,
            MutationTestSuitePreLoader(self.project))
        self.assertEqual(self.validity_check_stdout, fdbk.validity_check_stdout.read().decode())
        self.assertEqual(len(self.validity_check_stdout), fdbk.get_validity_check_stdout_size())

        self.mutation_suite.validate_and_update(
            normal_fdbk_config={'show_validity_check_stdout': False})
        fdbk = self.result.get_fdbk(
            ag_models.FeedbackCategory.normal,
            MutationTestSuitePreLoader(self.project))
        self.assertIsNone(fdbk.validity_check_stdout)
        self.assertIsNone(fdbk.get_validity_check_stdout_size())

    def test_show_and_hide_validity_check_stderr(self):
        self.mutation_suite.validate_and_update(
            normal_fdbk_config={'show_validity_check_stderr': True})
        fdbk = self.result.get_fdbk(
            ag_models.FeedbackCategory.normal,
            MutationTestSuitePreLoader(self.project))
        self.assertEqual(self.validity_check_stderr, fdbk.validity_check_stderr.read().decode())
        self.assertEqual(len(self.validity_check_stderr), fdbk.get_validity_check_stderr_size())

        self.mutation_suite.validate_and_update(
            normal_fdbk_config={'show_validity_check_stderr': False})
        fdbk = self.result.get_fdbk(
            ag_models.FeedbackCategory.normal,
            MutationTestSuitePreLoader(self.project))
        self.assertIsNone(fdbk.validity_check_stderr)
        self.assertIsNone(fdbk.get_validity_check_stdout_size())

    def test_show_and_hide_grade_impl_stdout(self):
        self.mutation_suite.validate_and_update(
            normal_fdbk_config={'show_grade_buggy_impls_stdout': True})
        fdbk = self.result.get_fdbk(
            ag_models.FeedbackCategory.normal,
            MutationTestSuitePreLoader(self.project))
        self.assertEqual(self.grade_buggy_impls_stdout,
                         fdbk.grade_buggy_impls_stdout.read().decode())
        self.assertEqual(len(self.grade_buggy_impls_stdout),
                         fdbk.get_grade_buggy_impls_stdout_size())

        self.mutation_suite.validate_and_update(
            normal_fdbk_config={'show_grade_buggy_impls_stdout': False})
        fdbk = self.result.get_fdbk(
            ag_models.FeedbackCategory.normal,
            MutationTestSuitePreLoader(self.project))
        self.assertIsNone(fdbk.grade_buggy_impls_stdout)
        self.assertIsNone(fdbk.get_grade_buggy_impls_stdout_size())

    def test_show_and_hide_grade_impl_stderr(self):
        self.mutation_suite.validate_and_update(
            normal_fdbk_config={'show_grade_buggy_impls_stderr': True})
        fdbk = self.result.get_fdbk(
            ag_models.FeedbackCategory.normal,
            MutationTestSuitePreLoader(self.project))
        self.assertEqual(self.grade_buggy_impls_stderr,
                         fdbk.grade_buggy_impls_stderr.read().decode())
        self.assertEqual(len(self.grade_buggy_impls_stderr),
                         fdbk.get_grade_buggy_impls_stderr_size())

        self.mutation_suite.validate_and_update(
            normal_fdbk_config={'show_grade_buggy_impls_stderr': False})
        fdbk = self.result.get_fdbk(
            ag_models.FeedbackCategory.normal,
            MutationTestSuitePreLoader(self.project))
        self.assertIsNone(fdbk.grade_buggy_impls_stderr)
        self.assertIsNone(fdbk.get_grade_buggy_impls_stderr_size())

    def test_show_and_hide_invalid_and_timed_out_test_names(self):
        self.mutation_suite.validate_and_update(
            normal_fdbk_config={'show_invalid_test_names': True})
        fdbk = self.result.get_fdbk(
            ag_models.FeedbackCategory.normal,
            MutationTestSuitePreLoader(self.project))
        self.assertSequenceEqual(self.student_tests, fdbk.student_tests)
        self.assertSequenceEqual(self.invalid_tests, fdbk.invalid_tests)
        self.assertSequenceEqual(self.timeout_tests, fdbk.timed_out_tests)

        self.mutation_suite.validate_and_update(
            normal_fdbk_config={'show_invalid_test_names': False})
        fdbk = self.result.get_fdbk(
            ag_models.FeedbackCategory.normal,
            MutationTestSuitePreLoader(self.project))
        self.assertSequenceEqual(self.student_tests, fdbk.student_tests)
        self.assertIsNone(fdbk.invalid_tests)
        self.assertIsNone(fdbk.timed_out_tests)

    def test_hide_points(self):
        self.mutation_suite.validate_and_update(normal_fdbk_config={'show_points': False})
        for fdbk_level in ag_models.BugsExposedFeedbackLevel:
            self.mutation_suite.validate_and_update(
                normal_fdbk_config={'bugs_exposed_fdbk_level': fdbk_level})

            fdbk = self.result.get_fdbk(
                ag_models.FeedbackCategory.normal,
                MutationTestSuitePreLoader(self.project))

            self.assertEqual(0, fdbk.total_points)
            self.assertEqual(0, fdbk.total_points_possible)

    def test_no_bugs_exposed_fdbk(self):
        self.mutation_suite.validate_and_update(
            normal_fdbk_config={
                'show_points': True,
                'bugs_exposed_fdbk_level': ag_models.BugsExposedFeedbackLevel.no_feedback
            }
        )

        fdbk = self.result.get_fdbk(
            ag_models.FeedbackCategory.normal,
            MutationTestSuitePreLoader(self.project))
        self.assertIsNone(fdbk.num_bugs_exposed)
        self.assertIsNone(fdbk.bugs_exposed)
        self.assertEqual(0, fdbk.total_points)
        self.assertEqual(0, fdbk.total_points_possible)

    def test_show_num_bugs_exposed(self):
        self.mutation_suite.validate_and_update(
            normal_fdbk_config={
                'show_points': True,
                'bugs_exposed_fdbk_level': ag_models.BugsExposedFeedbackLevel.num_bugs_exposed
            }
        )

        fdbk = self.result.get_fdbk(
            ag_models.FeedbackCategory.normal,
            MutationTestSuitePreLoader(self.project))
        self.assertEqual(len(self.bugs_exposed), fdbk.num_bugs_exposed)
        self.assertIsNone(fdbk.bugs_exposed)
        self.assertEqual(self.points_awarded, fdbk.total_points)
        self.assertEqual(self.points_possible, fdbk.total_points_possible)

    def test_show_exposed_bug_names(self):
        self.mutation_suite.validate_and_update(
            normal_fdbk_config={
                'show_points': True,
                'bugs_exposed_fdbk_level': ag_models.BugsExposedFeedbackLevel.exposed_bug_names
            }
        )

        fdbk = self.result.get_fdbk(
            ag_models.FeedbackCategory.normal,
            MutationTestSuitePreLoader(self.project))
        self.assertEqual(len(self.bugs_exposed), fdbk.num_bugs_exposed)
        self.assertSequenceEqual(self.bugs_exposed, fdbk.bugs_exposed)
        self.assertEqual(self.points_awarded, fdbk.total_points)
        self.assertEqual(self.points_possible, fdbk.total_points_possible)

    def test_max_points_upper_score_limit(self):
        max_points = (
            len(self.bug_names) * self.points_per_exposed_bug - self.points_per_exposed_bug)
        fdbk = self.result.get_fdbk(
            ag_models.FeedbackCategory.max,
            MutationTestSuitePreLoader(self.project))
        self.assertGreater(fdbk.total_points_possible, max_points)

        self.mutation_suite.validate_and_update(max_points=max_points)
        fdbk = self.result.get_fdbk(
            ag_models.FeedbackCategory.max,
            MutationTestSuitePreLoader(self.project))
        self.assertEqual(max_points, fdbk.total_points)
        self.assertEqual(max_points, fdbk.total_points_possible)

    def test_points_per_exposed_bug_float(self):
        self.mutation_suite.validate_and_update(points_per_exposed_bug='1.1')
        self.result.bugs_exposed = self.bug_names[:3]
        self.result.save()

        fdbk = self.result.get_fdbk(
            ag_models.FeedbackCategory.max,
            MutationTestSuitePreLoader(self.project))
        # Keep these magic numbers up to date with setUp.
        # Do NOT compute the expected result with multiplication.
        # These numbers have been specifically chosen to test
        # floating point issues.
        # Keep the use of assertEqual. Do NOT use assertAlmostEqual
        self.assertEqual(decimal.Decimal('3.3'), fdbk.total_points)
        self.assertEqual(decimal.Decimal('5.5'), fdbk.total_points_possible)

        self.assertEqual('3.30', fdbk.to_dict()['total_points'])
        self.assertEqual('5.50', fdbk.to_dict()['total_points_possible'])

    def test_serialization(self):
        expected_fields = [
            'pk',
            'mutation_test_suite_name',
            'mutation_test_suite_pk',
            'fdbk_settings',
            'has_setup_command',
            'setup_command_name',
            'setup_return_code',
            'setup_timed_out',
            'get_student_test_names_return_code',
            'get_student_test_names_timed_out',
            'student_tests',
            'discarded_tests',
            'invalid_tests',
            'timed_out_tests',
            'num_bugs_exposed',
            'bugs_exposed',
            'total_points',
            'total_points_possible',
        ]

        serialized = self.result.get_fdbk(
            ag_models.FeedbackCategory.max,
            MutationTestSuitePreLoader(self.project)).to_dict()
        self.assertCountEqual(expected_fields, serialized.keys())
