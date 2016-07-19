import datetime

from django.core.cache import cache
from django.utils import timezone

import autograder.core.models as ag_models
from autograder.core.models.autograder_test_case import feedback_config

from autograder.core.tests.temporary_filesystem_test_case import (
    TemporaryFilesystemTestCase)
import autograder.core.tests.dummy_object_utils as obj_ut

from autograder.core.tests.test_models.test_autograder_test_case.models \
    import _DummyAutograderTestCase


class AutograderTestCaseResultTestCase(TemporaryFilesystemTestCase):
    def setUp(self):
        super().setUp()

        self.closing_time = timezone.now() + datetime.timedelta(hours=-1)

        group = obj_ut.build_submission_group(
            project_kwargs={'closing_time': self.closing_time})
        self.project = group.project

        self.submission = ag_models.Submission.objects.validate_and_create(
            submission_group=group,
            submitted_files=[])

        self.test_name = 'my_test'
        self.test_case = _DummyAutograderTestCase.objects.validate_and_create(
            name=self.test_name,
            project=self.project)

    def test_default_init(self):
        result = ag_models.AutograderTestCaseResult.objects.create(
            test_case=self.test_case,
            submission=self.submission)

        result.refresh_from_db()

        self.assertEqual(result, result)

        self.assertEqual(result.test_case, self.test_case)
        self.assertIsNone(result.return_code)
        self.assertEqual(result.standard_output, '')
        self.assertEqual(result.standard_error_output, '')
        self.assertFalse(result.timed_out)
        self.assertIsNone(result.valgrind_return_code)
        self.assertEqual(result.valgrind_output, '')
        self.assertIsNone(result.compilation_return_code)
        self.assertEqual(result.compilation_standard_output, '')
        self.assertEqual(result.compilation_standard_error_output, '')


class TotalScoreTestCase(TemporaryFilesystemTestCase):
    def test_basic_score(self):
        cache.clear()
        result = obj_ut.build_compiled_ag_test_result()

        self.assertEqual(0, result.basic_score)

        result.test_case.validate_and_update(
            feedback_configuration=(
                feedback_config.FeedbackConfig.create_with_max_fdbk()))

        self.assertEqual(obj_ut.build_compiled_ag_test.points_with_all_used,
                         result.basic_score)

    def test_cache_invalidation(self):
        results = []
        result = obj_ut.build_compiled_ag_test_result()
        result.test_case.feedback_configuration = (
            feedback_config.FeedbackConfig.create_with_max_fdbk())
        results.append(result)

        test_case = result.test_case

        result = obj_ut.build_compiled_ag_test_result(
            test_case=test_case)
        result.test_case.feedback_configuration = (
            feedback_config.FeedbackConfig.create_with_max_fdbk())
        results.append(result)

        self.assertEqual(results[0].test_case, results[1].test_case)

        for result in results:
            self.assertEqual(
                obj_ut.build_compiled_ag_test.points_with_all_used,
                result.basic_score)

        test_case.points_for_correct_return_code += 1
        test_case.save()

        for result in results:
            self.assertEqual(
                obj_ut.build_compiled_ag_test.points_with_all_used + 1,
                result.basic_score)

        test_case.feedback_configuration.validate_and_update(
            points_fdbk=feedback_config.PointsFdbkLevel.hide)

        self.assertEqual(0, result.basic_score)
