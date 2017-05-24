import datetime
import random

from django.utils import timezone

from autograder.utils.testing import UnitTestBase

import autograder.core.models as ag_models

import autograder.utils.testing.model_obj_builders as obj_build


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
            [], submission_group=other_group)

    def test_no_daily_limit(self):
        self.assertIsNone(self.project.submission_limit_per_day)
        for i in range(10):
            sub = ag_models.Submission.objects.validate_and_create(
                [], submission_group=self.submission_group)
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
                [], submission_group=self.submission_group,
                timestamp=timestamp)
            self.assertTrue(sub.count_towards_daily_limit)
            self.assertFalse(sub.is_past_daily_limit)

        # Place submission at exact beginning of next cycle
        next_cycle_timestamp = timestamp + timezone.timedelta(days=1)
        sub = ag_models.Submission.objects.validate_and_create(
            [], submission_group=self.submission_group,
            timestamp=next_cycle_timestamp)
        self.assertTrue(sub.count_towards_daily_limit)
        self.assertFalse(sub.is_past_daily_limit)

    def test_past_daily_limit(self):
        limit = random.randint(2, 5)
        self.project.validate_and_update(submission_limit_per_day=limit)
        not_past_limit = []
        for i in range(limit):
            sub = ag_models.Submission.objects.validate_and_create(
                [], submission_group=self.submission_group)
            not_past_limit.append(sub)

        for i in range(2):
            sub = ag_models.Submission.objects.validate_and_create(
                [], submission_group=self.submission_group)

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
            [], submission_group=self.submission_group, timestamp=timestamp)
        sub.count_towards_daily_limit = False
        sub.save()
        submissions.append(sub)
        self.assertFalse(sub.count_towards_daily_limit)
        for i in range(limit):
            sub = ag_models.Submission.objects.validate_and_create(
                [], submission_group=self.submission_group,
                timestamp=timestamp)
            sub.count_towards_daily_limit = True
            sub.save()
            submissions.append(sub)
            self.assertTrue(sub.count_towards_daily_limit)

        for sub in submissions:
            self.assertFalse(sub.is_past_daily_limit)

    def test_group_submissions_towards_limit_count(self):
        limit = random.randint(3, 5)
        self.project.validate_and_update(submission_limit_per_day=limit)
        for i in range(limit + 2):
            self.assertEqual(
                i, self.submission_group.num_submits_towards_limit)
            sub = ag_models.Submission.objects.validate_and_create(
                [], submission_group=self.submission_group)
            self.assertTrue(sub.count_towards_daily_limit)
            if i > limit:
                self.assertTrue(sub.is_past_daily_limit)

        self.assertEqual(
            i + 1, self.submission_group.num_submits_towards_limit)

    def test_group_submissions_towards_limit_some_not_counted(self):
        limit = 3
        self.project.validate_and_update(submission_limit_per_day=limit)
        # We'll count every other submission towards the limit
        for i in range(limit * 2):
            count_towards_limit = i % 2 != 0

            sub = ag_models.Submission.objects.validate_and_create(
                [], submission_group=self.submission_group)
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
            [], submission_group=self.submission_group)
        self.assertTrue(sub.is_past_daily_limit)

    def test_is_past_limit_change_with_count_towards_limit(self):
        timestamp = timezone.now() + timezone.timedelta(days=-3)
        self.project.validate_and_update(submission_limit_per_day=1)

        old_sub = ag_models.Submission.objects.validate_and_create(
            [], submission_group=self.submission_group, timestamp=timestamp)
        old_sub.count_towards_daily_limit = False
        old_sub.save()
        self.assertEqual(0, self.submission_group.num_submits_towards_limit)
        self.assertFalse(old_sub.is_past_daily_limit)
        self.assertFalse(old_sub.count_towards_daily_limit)

        new_sub = ag_models.Submission.objects.validate_and_create(
            [], submission_group=self.submission_group, timestamp=timestamp)
        self.assertFalse(new_sub.is_past_daily_limit)
        self.assertTrue(new_sub.count_towards_daily_limit)

        # Marking the older submission as counting towards limit should
        # push the newer submission past the limit.
        old_sub.validate_and_update(count_towards_daily_limit=True)
        self.assertFalse(old_sub.is_past_daily_limit)
        self.assertTrue(new_sub.is_past_daily_limit)

        # Re-mark the older submission as not counting, which should
        # push the newer submission back below the limit.
        old_sub.validate_and_update(count_towards_daily_limit=False)
        self.assertFalse(old_sub.is_past_daily_limit)
        self.assertFalse(new_sub.is_past_daily_limit)

    def test_non_default_limit_reset_time(self):
        reset_datetime = timezone.datetime.combine(
            timezone.now().date(), datetime.time(hour=22))
        reset_datetime = reset_datetime.replace(tzinfo=timezone.now().tzinfo)
        self.project.validate_and_update(
            submission_limit_reset_time=reset_datetime.time(),
            submission_limit_per_day=1)

        old_timestamp = reset_datetime + timezone.timedelta(hours=-23)
        old_sub = ag_models.Submission.objects.validate_and_create(
            [], submission_group=self.submission_group,
            timestamp=old_timestamp)
        self.assertTrue(old_sub.count_towards_daily_limit)
        self.assertFalse(old_sub.is_past_daily_limit)

        new_timestamp = reset_datetime + timezone.timedelta(hours=-1)
        new_sub = ag_models.Submission.objects.validate_and_create(
            [], submission_group=self.submission_group,
            timestamp=new_timestamp)
        self.assertTrue(new_sub.count_towards_daily_limit)
        self.assertTrue(new_sub.is_past_daily_limit)

        next_cycle_timestamp = reset_datetime
        next_cycle_sub = ag_models.Submission.objects.validate_and_create(
            [], submission_group=self.submission_group,
            timestamp=next_cycle_timestamp)
        self.assertTrue(next_cycle_sub.count_towards_daily_limit)
        self.assertFalse(next_cycle_sub.is_past_daily_limit)

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
                [], submission_group=self.submission_group)
            submission.status = status
            submission.save()
            self.assertEqual(count,
                             self.submission_group.num_submits_towards_limit)
            self.assertFalse(submission.is_past_daily_limit)

        past_limit = ag_models.Submission.objects.validate_and_create(
            [], submission_group=self.submission_group)
        self.assertEqual(num_statuses + 1,
                         self.submission_group.num_submits_towards_limit)
        self.assertTrue(past_limit.is_past_daily_limit)

    def test_statuses_not_counted_towards_limit(self):
        self.project.validate_and_update(submission_limit_per_day=2)
        first_sub = ag_models.Submission.objects.validate_and_create(
            [], submission_group=self.submission_group)
        self.assertEqual(1, self.submission_group.num_submits_towards_limit)
        self.assertFalse(first_sub.is_past_daily_limit)

        removed_sub = ag_models.Submission.objects.validate_and_create(
            [], submission_group=self.submission_group)
        removed_sub.status = ag_models.Submission.GradingStatus.removed_from_queue
        removed_sub.save()
        self.assertEqual(1, self.submission_group.num_submits_towards_limit)
        self.assertFalse(removed_sub.is_past_daily_limit)

        error_sub = ag_models.Submission.objects.validate_and_create(
            [], submission_group=self.submission_group)
        error_sub.status = ag_models.Submission.GradingStatus.error
        error_sub.save()
        self.assertEqual(1, self.submission_group.num_submits_towards_limit)
        self.assertFalse(error_sub.is_past_daily_limit)

        second_sub = ag_models.Submission.objects.validate_and_create(
            [], submission_group=self.submission_group)
        self.assertEqual(2, self.submission_group.num_submits_towards_limit)
        self.assertFalse(second_sub.is_past_daily_limit)

        third_sub = ag_models.Submission.objects.validate_and_create(
            [], submission_group=self.submission_group)
        self.assertEqual(3, self.submission_group.num_submits_towards_limit)
        self.assertTrue(third_sub.is_past_daily_limit)
