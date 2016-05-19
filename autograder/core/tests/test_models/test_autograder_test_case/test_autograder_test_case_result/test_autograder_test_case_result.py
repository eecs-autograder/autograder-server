import datetime

from django.utils import timezone

import autograder.core.models as ag_models

from autograder.core.tests.temporary_filesystem_test_case import (
    TemporaryFilesystemTestCase)
import autograder.core.tests.dummy_object_utils as obj_ut

from autograder.core.tests.test_models.test_autograder_test_case.models import (
    _DummyAutograderTestCase)


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
