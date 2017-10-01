import itertools

import autograder.core.models as ag_models
from autograder.utils.testing import UnitTestBase
import autograder.utils.testing.model_obj_builders as obj_build


class StudentTestSuiteResultTestCase(UnitTestBase):
    def setUp(self):
        super().setUp()
        self.submission = obj_build.build_submission()
        self.project = self.submission.submission_group.project
        self.student_suite = ag_models.StudentTestSuite.objects.validate_and_create(
            name='qewirqwekljr', project=self.project)

    def test_default_init(self):
        result = ag_models.StudentTestSuiteResult.objects.validate_and_create(
            student_test_suite=self.student_suite, submission=self.submission)

        self.assertEqual(self.student_suite, result.student_test_suite)
        self.assertEqual(self.submission, result.submission)
        self.assertSequenceEqual([], result.valid_tests)
        self.assertSequenceEqual([], result.invalid_tests)
        self.assertSequenceEqual([], result.timed_out_tests)
        self.assertSequenceEqual([], result.bugs_exposed)
        self.assertIsNone(result.setup_result)

    def test_output_filenames_distinct(self):
        field_names = [
            'validity_check_stdout_filename',
            'validity_check_stderr_filename',
            'grade_buggy_impls_stdout_filename',
            'grade_buggy_impls_stderr_filename',
        ]

        result = ag_models.StudentTestSuiteResult.objects.validate_and_create(
            student_test_suite=self.student_suite, submission=self.submission)
        result2 = ag_models.StudentTestSuiteResult.objects.validate_and_create(
            student_test_suite=self.student_suite, submission=self.submission)

        for name in field_names:
            self.assertNotEqual(getattr(result, name), getattr(result2, name))


class StudentTestSuiteResultFeedbackTestCase(UnitTestBase):
    def setUp(self):
        super().setUp()
        self.submission = obj_build.build_submission()
        self.project = self.submission.submission_group.project

        self.bug_names = ['bug{}'.format(i) for i in range(5)]
        self.points_per_exposed_bug = 2
        self.points_possible = len(self.bug_names) * self.points_per_exposed_bug

        self.student_suite = ag_models.StudentTestSuite.objects.validate_and_create(
            name='adnfa;kdsfj', project=self.project,
            buggy_impl_names=self.bug_names,
            setup_command={
                'cmd': 'echo waaaluigi',
            },
            points_per_exposed_bug=self.points_per_exposed_bug,
        )  # type: ag_models.StudentTestSuite

        self.setup_stdout = 'adskfja;slekjaf'
        self.setup_stderr = 'amnak;sdjvaie'
        self.validity_check_stdout = 'aasdf'
        self.validity_check_stderr = 'lkjll'
        self.grade_buggy_impls_stdout = 'aoewij'
        self.grade_buggy_impls_stderr = 'cvasdop;f'

        self.setup_result = ag_models.AGCommandResult.objects.validate_and_create(
            ag_command=self.student_suite.setup_command)  # type: ag_models.AGCommandResult

        with self.setup_result.open_stdout('w') as f:
            f.write(self.setup_stdout)
        with self.setup_result.open_stderr('w') as f:
            f.write(self.setup_stderr)

        self.valid_tests = ['test{}'.format(i) for i in range(3)]
        self.invalid_tests = ['bad{}'.format(i) for i in range(4)]
        self.timeout_tests = ['not_sanic{}'.format(i) for i in range(2)]

        self.student_tests = self.valid_tests + self.invalid_tests + self.timeout_tests

        self.bugs_exposed = self.bug_names[:-1]
        self.points_awarded = len(self.bugs_exposed) * self.points_per_exposed_bug

        self.result = ag_models.StudentTestSuiteResult.objects.validate_and_create(
            student_test_suite=self.student_suite, submission=self.submission,
            student_tests=self.student_tests,
            invalid_tests=self.invalid_tests,
            timed_out_tests=self.timeout_tests,
            bugs_exposed=self.bugs_exposed,
            setup_result=self.setup_result
        )  # type: ag_models.StudentTestSuiteResult

        with self.result.open_validity_check_stdout('w') as f:
            f.write(self.validity_check_stdout)
        with self.result.open_validity_check_stderr('w') as f:
            f.write(self.validity_check_stderr)
        with self.result.open_grade_buggy_impls_stdout('w') as f:
            f.write(self.grade_buggy_impls_stdout)
        with self.result.open_grade_buggy_impls_stderr('w') as f:
            f.write(self.grade_buggy_impls_stderr)

    def test_feedback_calculator_factory_method(self):
        # check against the actual objects (their pks)
        self.assertEqual(
            self.student_suite.normal_fdbk_config,
            self.result.get_fdbk(ag_models.FeedbackCategory.normal).fdbk_conf)
        self.assertEqual(
            self.student_suite.ultimate_submission_fdbk_config,
            self.result.get_fdbk(ag_models.FeedbackCategory.ultimate_submission).fdbk_conf)
        self.assertEqual(
            self.student_suite.past_limit_submission_fdbk_config,
            self.result.get_fdbk(
                             ag_models.FeedbackCategory.past_limit_submission).fdbk_conf)
        self.assertEqual(
            self.student_suite.staff_viewer_fdbk_config,
            self.result.get_fdbk(ag_models.FeedbackCategory.staff_viewer).fdbk_conf)

        max_fdbk = self.result.get_fdbk(ag_models.FeedbackCategory.max).fdbk_conf
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

    def test_show_and_hide_setup_return_code(self):
        self.student_suite.normal_fdbk_config.validate_and_update(show_setup_return_code=True)

        self.result.setup_result.return_code = None
        self.result.setup_result.save()
        fdbk = self.result.get_fdbk(ag_models.FeedbackCategory.normal)
        self.assertIsNone(fdbk.setup_return_code)

        return_code = 31
        self.result.setup_result.return_code = return_code
        self.setup_result.save()
        fdbk = self.result.get_fdbk(ag_models.FeedbackCategory.normal)
        self.assertEqual(return_code, fdbk.setup_return_code)

        self.student_suite.normal_fdbk_config.validate_and_update(show_setup_return_code=False)

        fdbk = self.result.get_fdbk(ag_models.FeedbackCategory.normal)
        self.assertIsNone(fdbk.setup_return_code)

    def test_show_setup_return_code_but_no_setup_cmd(self):
        self.student_suite.validate_and_update(setup_command=None)
        self.student_suite.normal_fdbk_config.validate_and_update(show_setup_return_code=True)
        fdbk = self.result.get_fdbk(ag_models.FeedbackCategory.normal)
        self.assertIsNone(fdbk.setup_return_code)

    def test_show_and_hide_setup_stdout(self):
        self.student_suite.normal_fdbk_config.validate_and_update(show_setup_stdout=True)
        fdbk = self.result.get_fdbk(ag_models.FeedbackCategory.normal)
        self.assertEqual(self.setup_stdout, fdbk.setup_stdout.read().decode())

        self.student_suite.normal_fdbk_config.validate_and_update(show_setup_stdout=False)
        fdbk = self.result.get_fdbk(ag_models.FeedbackCategory.normal)
        self.assertIsNone(fdbk.setup_stdout)

    def test_show_and_hide_setup_stderr(self):
        self.student_suite.normal_fdbk_config.validate_and_update(show_setup_stderr=True)
        fdbk = self.result.get_fdbk(ag_models.FeedbackCategory.normal)
        self.assertEqual(self.setup_stderr, fdbk.setup_stderr.read().decode())

        self.student_suite.normal_fdbk_config.validate_and_update(show_setup_stderr=False)
        fdbk = self.result.get_fdbk(ag_models.FeedbackCategory.normal)
        self.assertIsNone(fdbk.setup_stderr)

    def test_show_setup_stdout_and_stderr_but_no_setup_cmd(self):
        self.student_suite.validate_and_update(setup_command=None)
        self.student_suite.normal_fdbk_config.validate_and_update(
            show_setup_stdout=True, show_setup_stderr=True)
        fdbk = self.result.get_fdbk(ag_models.FeedbackCategory.normal)
        self.assertIsNone(fdbk.setup_stdout)
        self.assertIsNone(fdbk.setup_stderr)

    def test_show_and_hide_validity_check_stdout(self):
        self.student_suite.normal_fdbk_config.validate_and_update(show_validity_check_stdout=True)
        fdbk = self.result.get_fdbk(ag_models.FeedbackCategory.normal)
        self.assertEqual(self.validity_check_stdout, fdbk.validity_check_stdout.read().decode())

        self.student_suite.normal_fdbk_config.validate_and_update(show_validity_check_stdout=False)
        fdbk = self.result.get_fdbk(ag_models.FeedbackCategory.normal)
        self.assertIsNone(fdbk.validity_check_stdout)

    def test_show_and_hide_validity_check_stderr(self):
        self.student_suite.normal_fdbk_config.validate_and_update(show_validity_check_stderr=True)
        fdbk = self.result.get_fdbk(ag_models.FeedbackCategory.normal)
        self.assertEqual(self.validity_check_stderr, fdbk.validity_check_stderr.read().decode())

        self.student_suite.normal_fdbk_config.validate_and_update(show_validity_check_stderr=False)
        fdbk = self.result.get_fdbk(ag_models.FeedbackCategory.normal)
        self.assertIsNone(fdbk.validity_check_stderr)

    def test_show_and_hide_grade_impl_stdout(self):
        self.student_suite.normal_fdbk_config.validate_and_update(
            show_grade_buggy_impls_stdout=True)
        fdbk = self.result.get_fdbk(ag_models.FeedbackCategory.normal)
        self.assertEqual(self.grade_buggy_impls_stdout,
                         fdbk.grade_buggy_impls_stdout.read().decode())

        self.student_suite.normal_fdbk_config.validate_and_update(
            show_grade_buggy_impls_stdout=False)
        fdbk = self.result.get_fdbk(ag_models.FeedbackCategory.normal)
        self.assertIsNone(fdbk.grade_buggy_impls_stdout)

    def test_show_and_hide_grade_impl_stderr(self):
        self.student_suite.normal_fdbk_config.validate_and_update(
            show_grade_buggy_impls_stderr=True)
        fdbk = self.result.get_fdbk(ag_models.FeedbackCategory.normal)
        self.assertEqual(self.grade_buggy_impls_stderr,
                         fdbk.grade_buggy_impls_stderr.read().decode())

        self.student_suite.normal_fdbk_config.validate_and_update(
            show_grade_buggy_impls_stderr=False)
        fdbk = self.result.get_fdbk(ag_models.FeedbackCategory.normal)
        self.assertIsNone(fdbk.grade_buggy_impls_stderr)

    def test_show_and_hide_invalid_and_timed_out_test_names(self):
        self.student_suite.normal_fdbk_config.validate_and_update(show_invalid_test_names=True)
        fdbk = self.result.get_fdbk(ag_models.FeedbackCategory.normal)
        self.assertSequenceEqual(self.student_tests, fdbk.student_tests)
        self.assertSequenceEqual(self.invalid_tests, fdbk.invalid_tests)
        self.assertSequenceEqual(self.timeout_tests, fdbk.timed_out_tests)

        self.student_suite.normal_fdbk_config.validate_and_update(show_invalid_test_names=False)
        fdbk = self.result.get_fdbk(ag_models.FeedbackCategory.normal)
        self.assertSequenceEqual(self.student_tests, fdbk.student_tests)
        self.assertIsNone(fdbk.invalid_tests)
        self.assertIsNone(fdbk.timed_out_tests)

    def test_hide_points(self):
        self.student_suite.normal_fdbk_config.validate_and_update(show_points=False)
        for fdbk_level in ag_models.BugsExposedFeedbackLevel:
            self.student_suite.normal_fdbk_config.validate_and_update(
                bugs_exposed_fdbk_level=fdbk_level)

            fdbk = self.result.get_fdbk(ag_models.FeedbackCategory.normal)

            self.assertIsNone(fdbk.total_points)
            self.assertIsNone(fdbk.total_points_possible)

    def test_no_bugs_exposed_fdbk(self):
        self.student_suite.normal_fdbk_config.validate_and_update(
            show_points=True,
            bugs_exposed_fdbk_level=ag_models.BugsExposedFeedbackLevel.no_feedback)

        fdbk = self.result.get_fdbk(ag_models.FeedbackCategory.normal)
        self.assertIsNone(fdbk.num_bugs_exposed)
        self.assertIsNone(fdbk.bugs_exposed)
        self.assertIsNone(fdbk.total_points)
        self.assertIsNone(fdbk.total_points_possible)

    def test_show_num_bugs_exposed(self):
        self.student_suite.normal_fdbk_config.validate_and_update(
            show_points=True,
            bugs_exposed_fdbk_level=ag_models.BugsExposedFeedbackLevel.num_bugs_exposed)

        fdbk = self.result.get_fdbk(ag_models.FeedbackCategory.normal)
        self.assertEqual(len(self.bugs_exposed), fdbk.num_bugs_exposed)
        self.assertIsNone(fdbk.bugs_exposed)
        self.assertEqual(self.points_awarded, fdbk.total_points)
        self.assertEqual(self.points_possible, fdbk.total_points_possible)

    def test_show_exposed_bug_names(self):
        self.student_suite.normal_fdbk_config.validate_and_update(
            show_points=True,
            bugs_exposed_fdbk_level=ag_models.BugsExposedFeedbackLevel.exposed_bug_names)

        fdbk = self.result.get_fdbk(ag_models.FeedbackCategory.normal)
        self.assertEqual(len(self.bugs_exposed), fdbk.num_bugs_exposed)
        self.assertSequenceEqual(self.bugs_exposed, fdbk.bugs_exposed)
        self.assertEqual(self.points_awarded, fdbk.total_points)
        self.assertEqual(self.points_possible, fdbk.total_points_possible)

    def test_max_points_upper_score_limit(self):
        max_points = (
            len(self.bug_names) * self.points_per_exposed_bug - self.points_per_exposed_bug)
        fdbk = self.result.get_fdbk(ag_models.FeedbackCategory.max)
        self.assertGreater(fdbk.total_points_possible, max_points)

        self.student_suite.validate_and_update(max_points=max_points)
        fdbk = self.result.get_fdbk(ag_models.FeedbackCategory.max)
        self.assertEqual(max_points, fdbk.total_points)
        self.assertEqual(max_points, fdbk.total_points_possible)
