from unittest import mock

from django.urls import reverse
from django.test import tag

from rest_framework import status
from rest_framework.test import APIClient

import autograder.core.models as ag_models
import autograder.utils.testing.model_obj_builders as obj_build
from autograder.utils.testing import UnitTestBase, sleeper_subtest

from autograder.grading_tasks import tasks


@tag('slow')
class RaceConditionTestCase(UnitTestBase):
    def test_remove_from_queue_when_being_marked_as_being_graded_race_condition_prevented(self):
        group = obj_build.make_group(members_role=obj_build.UserRole.admin)
        submission = obj_build.build_submission(submission_group=group)

        path = ('autograder.core.models'
                '.Submission.GradingStatus.removed_from_queue')

        @sleeper_subtest(
            path,
            new_callable=mock.PropertyMock,
            return_value=(ag_models.Submission.GradingStatus.removed_from_queue))
        def do_request_and_wait():
            tasks.grade_submission(submission.pk)

        subtest = do_request_and_wait()

        print('sending remove from queue request')
        client = APIClient()
        client.force_authenticate(
            submission.submission_group.members.first())
        response = client.post(reverse('submission-remove-from-queue',
                                       kwargs={'pk': submission.pk}))
        subtest.join()
        submission.refresh_from_db()
        self.assertNotEqual(
            ag_models.Submission.GradingStatus.removed_from_queue,
            submission.status)
        self.assertEqual(status.HTTP_400_BAD_REQUEST, response.status_code)

        self.assertEqual(ag_models.Submission.GradingStatus.finished_grading,
                         submission.status)
