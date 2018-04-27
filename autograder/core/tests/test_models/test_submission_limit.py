import random

from django.utils import timezone

import autograder.core.models as ag_models
import autograder.utils.testing.model_obj_builders as obj_build
from autograder.utils.testing import UnitTestBase


class SubmissionLimitAndCountTestCase(UnitTestBase):
    def setUp(self):
        super().setUp()
        self.submission_group = obj_build.build_submission_group()
        self.project = self.submission_group.project

        # We want to make sure that only submissions for the specified
        # group are counted, so we'll create an extra other submission
        # to make sure it isn't counted.
        other_group = obj_build.build_submission_group()
        self.assertNotEqual(other_group, self.submission_group)
        ag_models.Submission.objects.validate_and_create(
            [], group=other_group)

    def test_no_daily_limit(self):
        self.assertIsNone(self.project.submission_limit_per_day)
        for i in range(10):
            sub = ag_models.Submission.objects.validate_and_create(
                [], group=self.submission_group)
            self.assertTrue(sub.count_towards_daily_limit)
            self.assertFalse(sub.is_past_daily_limit)

    def test_not_past_daily_limit(self):
        limit = random.randint(2, 5)
        self.project.validate_and_update(submission_limit_per_day=limit)
        timestamp = timezone.datetime.combine(
            timezone.now().date(), self.project.submission_limit_reset_time)
        timestamp = timestamp.replace(tzinfo=timezone.now().tzinfo)
        for i in range(limit):
            sub = ag_models.Submission.objects.validate_and_create(
                [], group=self.submission_group,
                timestamp=timestamp)
            self.assertTrue(sub.count_towards_daily_limit)
            self.assertFalse(sub.is_past_daily_limit)

        # Place submission at exact beginning of next cycle
        next_cycle_timestamp = timestamp + timezone.timedelta(days=1)
        sub = ag_models.Submission.objects.validate_and_create(
            [], group=self.submission_group,
            timestamp=next_cycle_timestamp)
        self.assertTrue(sub.count_towards_daily_limit)
        self.assertFalse(sub.is_past_daily_limit)

    def test_past_daily_limit(self):
        limit = random.randint(2, 5)
        self.project.validate_and_update(submission_limit_per_day=limit)
        not_past_limit = []
        for i in range(limit):
            sub = ag_models.Submission.objects.validate_and_create(
                [], group=self.submission_group)
            not_past_limit.append(sub)

        for i in range(2):
            sub = ag_models.Submission.objects.validate_and_create(
                [], group=self.submission_group)

            self.assertTrue(sub.count_towards_daily_limit)
            self.assertTrue(sub.is_past_daily_limit)

        # Verify that the status of earlier submissions hasn't changed
        for sub in not_past_limit:
            self.assertTrue(sub.count_towards_daily_limit)
            self.assertFalse(sub.is_past_daily_limit)

    def test_submission_limit_from_past_day(self):
        timestamp = timezone.now() + timezone.timedelta(days=-3)
        limit = 2
        self.project.validate_and_update(submission_limit_per_day=limit)
        submissions = []
        sub = ag_models.Submission.objects.validate_and_create(
            [], group=self.submission_group, timestamp=timestamp)
        sub.count_towards_daily_limit = False
        sub.save()
        submissions.append(sub)
        self.assertFalse(sub.count_towards_daily_limit)
        for i in range(limit):
            sub = ag_models.Submission.objects.validate_and_create(
                [], group=self.submission_group,
                timestamp=timestamp)
            sub.count_towards_daily_limit = True
            sub.save()
            submissions.append(sub)
            self.assertTrue(sub.count_towards_daily_limit)

        for sub in submissions:
            self.assertFalse(sub.is_past_daily_limit)

    def test_num_submits_towards_limit(self):
        limit = random.randint(3, 5)
        self.project.validate_and_update(submission_limit_per_day=limit)
        for i in range(limit + 2):
            self.assertEqual(
                i, self.submission_group.num_submits_towards_limit)
            sub = ag_models.Submission.objects.validate_and_create(
                [], group=self.submission_group)
            self.assertTrue(sub.count_towards_daily_limit)
            if i > limit:
                self.assertTrue(sub.is_past_daily_limit)

        self.assertEqual(
            i + 1, self.submission_group.num_submits_towards_limit)

    def test_num_submits_towards_limit_non_default_timezone(self):
        local_timezone = 'America/Chicago'
        now = timezone.now()
        now_local = now.astimezone(timezone.pytz.timezone(local_timezone))

        self.project.validate_and_update(
            submission_limit_reset_time=now_local - timezone.timedelta(minutes=5),
            submission_limit_reset_timezone=local_timezone)

        before_reset_time_submission = obj_build.build_submission(
            group=self.submission_group,
            timestamp=now - timezone.timedelta(hours=1))
        after_reset_time_submission = obj_build.build_submission(
            group=self.submission_group,
            timestamp=now + timezone.timedelta(hours=1))

        self.assertEqual(1, self.submission_group.num_submits_towards_limit)

    def test_group_submissions_towards_limit_some_not_counted(self):
        limit = 3
        self.project.validate_and_update(submission_limit_per_day=limit)
        # We'll count every other submission towards the limit
        for i in range(limit * 2):
            count_towards_limit = i % 2 != 0

            sub = ag_models.Submission.objects.validate_and_create(
                [], group=self.submission_group)
            sub.count_towards_daily_limit = count_towards_limit
            sub.save()
            self.assertEqual(count_towards_limit,
                             sub.count_towards_daily_limit)
            self.assertFalse(sub.is_past_daily_limit)

            # The number of submits towards the limit should increase by
            # 1 every other submission.
            self.assertEqual((i + 1) // 2,
                             self.submission_group.num_submits_towards_limit)

        sub = ag_models.Submission.objects.validate_and_create(
            [], group=self.submission_group)
        self.assertTrue(sub.is_past_daily_limit)

    def test_non_default_limit_reset_time_and_timezone(self):
        reset_timezone = 'America/Detroit'
        reset_datetime = timezone.now().astimezone(
            timezone.pytz.timezone(reset_timezone)
        ).replace(hour=22)
        self.project.validate_and_update(
            submission_limit_reset_time=reset_datetime.time(),
            submission_limit_reset_timezone=reset_timezone,
            submission_limit_per_day=1)

        within_limit_timestamp = reset_datetime + timezone.timedelta(hours=-23)
        within_limit_submission = ag_models.Submission.objects.validate_and_create(
            [], group=self.submission_group,
            timestamp=within_limit_timestamp)
        self.assertTrue(within_limit_submission.count_towards_daily_limit)
        self.assertFalse(within_limit_submission.is_past_daily_limit)

        past_limit_timestamp = reset_datetime + timezone.timedelta(hours=-1)
        past_limit_submission = ag_models.Submission.objects.validate_and_create(
            [], group=self.submission_group,
            timestamp=past_limit_timestamp)
        self.assertTrue(past_limit_submission.count_towards_daily_limit)
        self.assertTrue(past_limit_submission.is_past_daily_limit)

        next_cycle_timestamp = reset_datetime
        next_cycle_submission = ag_models.Submission.objects.validate_and_create(
            [], group=self.submission_group,
            timestamp=next_cycle_timestamp)
        self.assertTrue(next_cycle_submission.count_towards_daily_limit)
        self.assertFalse(next_cycle_submission.is_past_daily_limit)

    def test_statuses_counted_towards_limit(self):
        count_towards_limit_statuses = [
            ag_models.Submission.GradingStatus.received,
            ag_models.Submission.GradingStatus.queued,
            ag_models.Submission.GradingStatus.being_graded,
            ag_models.Submission.GradingStatus.waiting_for_deferred,
            ag_models.Submission.GradingStatus.finished_grading
        ]
        self.assertCountEqual(
            count_towards_limit_statuses,
            ag_models.Submission.GradingStatus.count_towards_limit_statuses)
        num_statuses = len(count_towards_limit_statuses)
        self.project.validate_and_update(submission_limit_per_day=num_statuses)

        for count, status in zip(range(1, num_statuses + 1),
                                 count_towards_limit_statuses):
            submission = ag_models.Submission.objects.validate_and_create(
                [], group=self.submission_group)
            submission.status = status
            submission.save()
            self.assertEqual(count,
                             self.submission_group.num_submits_towards_limit)
            self.assertFalse(submission.is_past_daily_limit)

        past_limit = ag_models.Submission.objects.validate_and_create(
            [], group=self.submission_group)
        self.assertEqual(num_statuses + 1,
                         self.submission_group.num_submits_towards_limit)
        self.assertTrue(past_limit.is_past_daily_limit)

    def test_statuses_not_counted_towards_limit(self):
        self.project.validate_and_update(submission_limit_per_day=2)
        first_sub = ag_models.Submission.objects.validate_and_create(
            [], group=self.submission_group)
        self.assertEqual(1, self.submission_group.num_submits_towards_limit)
        self.assertFalse(first_sub.is_past_daily_limit)

        removed_sub = ag_models.Submission.objects.validate_and_create(
            [], group=self.submission_group)
        removed_sub.status = ag_models.Submission.GradingStatus.removed_from_queue
        removed_sub.save()
        self.assertEqual(1, self.submission_group.num_submits_towards_limit)
        self.assertFalse(removed_sub.is_past_daily_limit)

        error_sub = ag_models.Submission.objects.validate_and_create(
            [], group=self.submission_group)
        error_sub.status = ag_models.Submission.GradingStatus.error
        error_sub.save()
        self.assertEqual(1, self.submission_group.num_submits_towards_limit)
        self.assertFalse(error_sub.is_past_daily_limit)

        second_sub = ag_models.Submission.objects.validate_and_create(
            [], group=self.submission_group)
        self.assertEqual(2, self.submission_group.num_submits_towards_limit)
        self.assertFalse(second_sub.is_past_daily_limit)

        third_sub = ag_models.Submission.objects.validate_and_create(
            [], group=self.submission_group)
        self.assertEqual(3, self.submission_group.num_submits_towards_limit)
        self.assertTrue(third_sub.is_past_daily_limit)
