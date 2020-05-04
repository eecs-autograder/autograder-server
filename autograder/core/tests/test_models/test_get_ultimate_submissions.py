import sys
from typing import List

import autograder.core.models as ag_models
import autograder.utils.testing.model_obj_builders as obj_build
from autograder.core.models.get_ultimate_submissions import (
    get_ultimate_submissions, get_ultimate_submission)
from autograder.core.submission_feedback import (
    update_denormalized_ag_test_results, AGTestPreLoader)
from autograder.core.tests.test_submission_feedback.fdbk_getter_shortcuts import (
    get_submission_fdbk)
from autograder.utils.testing import UnitTestBase


class _TestCase(UnitTestBase):
    class GroupAndSubmissionData:
        def __init__(self, group: ag_models.Group,
                     best_submission: ag_models.Submission,
                     most_recent_submission: ag_models.Submission):
            self.group = group
            self.best_submission = best_submission
            self.most_recent_submission = most_recent_submission

    def prepare_data(self, project: ag_models.Project,
                     num_suites=1,
                     cases_per_suite=1,
                     cmds_per_suite=1,
                     num_groups=1,
                     num_other_submissions=0) -> List[GroupAndSubmissionData]:
        cmds = []
        for i in range(num_suites):
            sys.stdout.write('\rBuilding suite {}'.format(i))
            sys.stdout.flush()
            suite = obj_build.make_ag_test_suite(project)
            for j in range(cases_per_suite):
                case = obj_build.make_ag_test_case(suite)
                for k in range(cmds_per_suite):
                    cmd = obj_build.make_full_ag_test_command(case)
                    cmds.append(cmd)

        group_and_submission_data = []
        for i in range(num_groups):
            sys.stdout.write('\rBuilding group {}'.format(i))
            sys.stdout.flush()
            group = obj_build.make_group(project=project)
            best_sub = obj_build.make_finished_submission(group=group)
            for cmd in cmds:
                obj_build.make_correct_ag_test_command_result(cmd, submission=best_sub)
            best_sub = update_denormalized_ag_test_results(best_sub.pk)

            for j in range(num_other_submissions):
                sub = obj_build.make_finished_submission(group=group)
                for cmd in cmds:
                    obj_build.make_incorrect_ag_test_command_result(cmd, submission=sub)
                sub = update_denormalized_ag_test_results(sub.pk)

            most_recent = obj_build.make_finished_submission(group=group)
            for cmd in cmds:
                obj_build.make_incorrect_ag_test_command_result(cmd, submission=most_recent)
            most_recent = update_denormalized_ag_test_results(most_recent.pk)

            group_and_submission_data.append(
                self.GroupAndSubmissionData(group, best_sub, most_recent))

        return group_and_submission_data


class GetUltimateSubmissionsTestCase(_TestCase):
    def setUp(self):
        super().setUp()
        self.project = obj_build.make_project()

        # Make sure we use the right group queryset
        other_project = obj_build.make_project(course=self.project.course)
        other_group = obj_build.make_group(project=other_project)
        other_subimssion = obj_build.make_finished_submission(other_group)

    def test_get_ultimate_submissions_group_filter_is_none_uses_all_groups(self):
        data = self.prepare_data(self.project, num_groups=3)
        groups = [datum.group for datum in data]
        expected_most_recents = [datum.most_recent_submission for datum in data]
        expected_bests = [datum.best_submission for datum in data]

        self.assertEqual(ag_models.UltimateSubmissionPolicy.most_recent,
                         self.project.ultimate_submission_policy)
        ultimate_most_recents = get_ultimate_submissions(
            self.project, filter_groups=None, ag_test_preloader=AGTestPreLoader(self.project))
        self.assertCountEqual(
            expected_most_recents, [fdbk.submission for fdbk in ultimate_most_recents])

        self.project.validate_and_update(
            ultimate_submission_policy=ag_models.UltimateSubmissionPolicy.best)
        ultimate_bests = get_ultimate_submissions(
            self.project, filter_groups=None, ag_test_preloader=AGTestPreLoader(self.project))
        self.assertCountEqual(expected_bests, [fdbk.submission for fdbk in ultimate_bests])

    def test_get_ultimate_submissions_group_subset_specified(self):
        data = self.prepare_data(self.project, num_groups=3)[:2]
        groups = [datum.group for datum in data]
        expected_most_recents = [datum.most_recent_submission for datum in data]
        expected_bests = [datum.best_submission for datum in data]

        self.assertEqual(ag_models.UltimateSubmissionPolicy.most_recent,
                         self.project.ultimate_submission_policy)
        ultimate_most_recents = get_ultimate_submissions(
            self.project, filter_groups=groups, ag_test_preloader=AGTestPreLoader(self.project))
        self.assertCountEqual(
            expected_most_recents, [fdbk.submission for fdbk in ultimate_most_recents])

        self.project.validate_and_update(
            ultimate_submission_policy=ag_models.UltimateSubmissionPolicy.best)
        ultimate_bests = get_ultimate_submissions(
            self.project, filter_groups=groups, ag_test_preloader=AGTestPreLoader(self.project))
        self.assertCountEqual(expected_bests, [fdbk.submission for fdbk in ultimate_bests])

    def test_get_ultimate_submissions_only_finished_grading_status_considered(self):
        data = self.prepare_data(self.project, num_groups=2)

        non_considered_statuses = filter(
            lambda val: val != ag_models.Submission.GradingStatus.finished_grading,
            ag_models.Submission.GradingStatus.values)

        for item in data:
            for grading_status in non_considered_statuses:
                obj_build.make_submission(group=item.group, status=grading_status)

        self.project.validate_and_update(
            ultimate_submission_policy=ag_models.UltimateSubmissionPolicy.most_recent)
        self.assertCountEqual(
            [item.most_recent_submission for item in data],
            [fdbk.submission for fdbk in
             get_ultimate_submissions(self.project,
                                      filter_groups=None,
                                      ag_test_preloader=AGTestPreLoader(self.project))])

        self.project.validate_and_update(
            ultimate_submission_policy=ag_models.UltimateSubmissionPolicy.best)
        self.assertCountEqual(
            [item.best_submission for item in data],
            [fdbk.submission for fdbk in
             get_ultimate_submissions(self.project,
                                      filter_groups=None,
                                      ag_test_preloader=AGTestPreLoader(self.project))])

    def test_get_ultimate_submission_group_has_no_submissions(self):
        group_with_submissions_data = self.prepare_data(self.project)[0]

        self.project.validate_and_update(
            ultimate_submission_policy=ag_models.UltimateSubmissionPolicy.most_recent)
        group_with_no_submissions = obj_build.make_group(project=self.project)

        self.assertEqual(0, group_with_no_submissions.submissions.count())
        ultimate_submission = get_ultimate_submission(group_with_no_submissions)
        self.assertIsNone(ultimate_submission)

        ultimate_submissions = [
            fdbk.submission for fdbk in
            get_ultimate_submissions(
                self.project, filter_groups=None, ag_test_preloader=AGTestPreLoader(self.project))
        ]
        self.assertSequenceEqual([group_with_submissions_data.most_recent_submission],
                                 ultimate_submissions)

        self.project.validate_and_update(
            ultimate_submission_policy=ag_models.UltimateSubmissionPolicy.best)

        self.assertEqual(0, group_with_no_submissions.submissions.count())
        ultimate_submission = get_ultimate_submission(group_with_no_submissions)
        self.assertIsNone(ultimate_submission)

        ultimate_submissions = [
            fdbk.submission for fdbk in
            get_ultimate_submissions(
                self.project, filter_groups=None, ag_test_preloader=AGTestPreLoader(self.project))
        ]
        self.assertSequenceEqual([group_with_submissions_data.best_submission],
                                 ultimate_submissions)

    def test_get_ultimate_submission_no_finished_submissions(self):
        group_with_finished_submissions_data = self.prepare_data(self.project)[0]

        group_with_no_finished_submissions = obj_build.make_group(project=self.project)
        unfinished_submission = obj_build.make_submission(group=group_with_no_finished_submissions)

        self.project.validate_and_update(
            ultimate_submission_policy=ag_models.UltimateSubmissionPolicy.most_recent)

        self.assertEqual(1, group_with_no_finished_submissions.submissions.count())
        self.assertNotEqual(
            ag_models.Submission.GradingStatus.finished_grading, unfinished_submission.status)
        ultimate_submissions = [
            fdbk.submission for fdbk in
            get_ultimate_submissions(self.project,
                                     filter_groups=None,
                                     ag_test_preloader=AGTestPreLoader(self.project))
        ]
        self.assertSequenceEqual([group_with_finished_submissions_data.most_recent_submission],
                                 ultimate_submissions)

        self.project.validate_and_update(
            ultimate_submission_policy=ag_models.UltimateSubmissionPolicy.best)

        self.assertEqual(1, group_with_no_finished_submissions.submissions.count())
        self.assertNotEqual(
            ag_models.Submission.GradingStatus.finished_grading, unfinished_submission.status)
        ultimate_submissions = [
            fdbk.submission for fdbk in
            get_ultimate_submissions(self.project,
                                     filter_groups=None,
                                     ag_test_preloader=AGTestPreLoader(self.project))
        ]
        self.assertSequenceEqual([group_with_finished_submissions_data.best_submission],
                                 ultimate_submissions)


class GetUltimateSubmissionTestCase(_TestCase):
    def setUp(self):
        super().setUp()
        self.project = obj_build.make_project()

    def test_get_ultimate_submission(self):
        data = self.prepare_data(self.project)
        group = data[0].group
        best_sub = data[0].best_submission
        most_recent = data[0].most_recent_submission

        print(group.submissions.count())
        print(group.submissions.all())

        self.assertEqual(ag_models.UltimateSubmissionPolicy.most_recent,
                         self.project.ultimate_submission_policy)
        ultimate_most_recent = get_ultimate_submission(group)
        self.assertEqual(most_recent, ultimate_most_recent)

        self.project.validate_and_update(
            ultimate_submission_policy=ag_models.UltimateSubmissionPolicy.best)
        ultimate_best = get_ultimate_submission(group)
        self.assertEqual(best_sub, ultimate_best)

    def test_get_ultimate_only_finished_grading_status_considered(self):
        group = obj_build.make_group(project=self.project)
        ultimate_submission = obj_build.make_finished_submission(group=group)
        non_considered_statuses = filter(
            lambda val: val != ag_models.Submission.GradingStatus.finished_grading,
            ag_models.Submission.GradingStatus.values)
        for grading_status in non_considered_statuses:
            obj_build.make_submission(group=group, status=grading_status)

        self.assertEqual(
            1,
            ag_models.Submission.objects.filter(
                status=ag_models.Submission.GradingStatus.finished_grading).count())

        for ultimate_submission_policy in ag_models.UltimateSubmissionPolicy:
            self.project.validate_and_update(ultimate_submission_policy=ultimate_submission_policy)
            self.assertSequenceEqual(
                [ultimate_submission],
                [fdbk.submission for fdbk in
                 get_ultimate_submissions(self.project,
                                          filter_groups=None,
                                          ag_test_preloader=AGTestPreLoader(self.project))])

    def test_get_ultimate_submission_group_has_no_submissions(self):
        for policy in ag_models.UltimateSubmissionPolicy:
            self.project.validate_and_update(ultimate_submission_policy=policy)
            group = obj_build.make_group(project=self.project)

            self.assertEqual(0, group.submissions.count())
            ultimate_submission = get_ultimate_submission(group)
            self.assertIsNone(ultimate_submission)

            ultimate_submissions = list(
                get_ultimate_submissions(self.project,
                                         filter_groups=[group],
                                         ag_test_preloader=AGTestPreLoader(self.project)))
            self.assertSequenceEqual([], ultimate_submissions)

    def test_get_ultimate_submission_no_finished_submissions(self):
        for policy in ag_models.UltimateSubmissionPolicy:
            self.project.validate_and_update(ultimate_submission_policy=policy)
            group = obj_build.make_group(project=self.project)
            submission = obj_build.make_submission(group=group)

            self.assertEqual(1, group.submissions.count())
            self.assertNotEqual(
                ag_models.Submission.GradingStatus.finished_grading, submission.status)
            ultimate_submission = get_ultimate_submission(group)
            self.assertIsNone(ultimate_submission)


class GetUltimateSubmissionForUserTestCase(UnitTestBase):
    def setUp(self):
        super().setUp()
        self.project = obj_build.make_project()
        self.course = self.project.course

        self.counts_for_user = obj_build.make_student_user(self.course)
        self.does_not_count_for_user = obj_build.make_student_user(self.course)

        self.group = ag_models.Group.objects.validate_and_create(
            members=[self.counts_for_user, self.does_not_count_for_user],
            project=self.project,
            check_group_size_limits=False,
        )

    def test_most_recent_does_not_count_for_user(self):
        self.project.validate_and_update(
            ultimate_submission_policy=ag_models.UltimateSubmissionPolicy.most_recent)

        oldest_submission = obj_build.make_finished_submission(self.group)
        most_recent_submission = obj_build.make_finished_submission(
            self.group, does_not_count_for=[self.does_not_count_for_user.username]
        )

        counts_for_user_ultimate_submission = get_ultimate_submission(
            self.group, user=self.counts_for_user
        )
        self.assertEqual(most_recent_submission, counts_for_user_ultimate_submission)

        does_not_count_for_user_ultimate_submission = get_ultimate_submission(
            self.group, user=self.does_not_count_for_user
        )
        self.assertEqual(oldest_submission, does_not_count_for_user_ultimate_submission)

    def test_two_most_recent_dont_count_for_user(self):
        self.project.validate_and_update(
            ultimate_submission_policy=ag_models.UltimateSubmissionPolicy.most_recent)

        oldest_submission = obj_build.make_finished_submission(self.group)
        middle_submission = obj_build.make_finished_submission(
            self.group, does_not_count_for=[self.does_not_count_for_user.username]
        )
        most_recent_submission = obj_build.make_finished_submission(
            self.group, does_not_count_for=[self.does_not_count_for_user.username]
        )

        counts_for_user_ultimate_submission = get_ultimate_submission(
            self.group, user=self.counts_for_user
        )
        self.assertEqual(most_recent_submission, counts_for_user_ultimate_submission)

        does_not_count_for_user_ultimate_submission = get_ultimate_submission(
            self.group, user=self.does_not_count_for_user
        )
        self.assertEqual(oldest_submission, does_not_count_for_user_ultimate_submission)

    def test_best_does_not_count_for_user(self):
        self.project.validate_and_update(
            ultimate_submission_policy=ag_models.UltimateSubmissionPolicy.best)

        suite = ag_models.MutationTestSuite.objects.validate_and_create(
            name='suite', project=self.project, buggy_impl_names=[f'bug{i}' for i in range(3)],
            points_per_exposed_bug=1
        )

        best_submission = obj_build.make_finished_submission(
            self.group, does_not_count_for=[self.does_not_count_for_user.username])
        ag_models.MutationTestSuiteResult.objects.validate_and_create(
            student_test_suite=suite,
            submission=best_submission, bugs_exposed=suite.buggy_impl_names
        )
        self.assertEqual(
            3, get_submission_fdbk(best_submission, ag_models.FeedbackCategory.max).total_points)

        other_submission = obj_build.make_finished_submission(self.group)
        self.assertEqual(
            0, get_submission_fdbk(other_submission, ag_models.FeedbackCategory.max).total_points)

        counts_for_user_ultimate_submission = get_ultimate_submission(
            self.group, user=self.counts_for_user
        )
        self.assertEqual(best_submission, counts_for_user_ultimate_submission)

        does_not_count_for_user_ultimate_submission = get_ultimate_submission(
            self.group, user=self.does_not_count_for_user
        )
        self.assertEqual(other_submission, does_not_count_for_user_ultimate_submission)

    def test_two_best_dont_count_for_user(self):
        self.project.validate_and_update(
            ultimate_submission_policy=ag_models.UltimateSubmissionPolicy.best)

        suite = ag_models.MutationTestSuite.objects.validate_and_create(
            name='suite', project=self.project, buggy_impl_names=[f'bug{i}' for i in range(3)],
            points_per_exposed_bug=1
        )

        best_submission = obj_build.make_finished_submission(
            self.group, does_not_count_for=[self.does_not_count_for_user.username])
        ag_models.MutationTestSuiteResult.objects.validate_and_create(
            student_test_suite=suite,
            submission=best_submission, bugs_exposed=suite.buggy_impl_names
        )
        self.assertEqual(
            3, get_submission_fdbk(best_submission, ag_models.FeedbackCategory.max).total_points)

        second_best_submission = obj_build.make_finished_submission(
            self.group, does_not_count_for=[self.does_not_count_for_user.username])
        ag_models.MutationTestSuiteResult.objects.validate_and_create(
            student_test_suite=suite,
            submission=second_best_submission, bugs_exposed=suite.buggy_impl_names[:-1]
        )
        self.assertEqual(
            2, get_submission_fdbk(second_best_submission,
                                   ag_models.FeedbackCategory.max).total_points)

        other_submission = obj_build.make_finished_submission(self.group)
        self.assertEqual(
            0, get_submission_fdbk(other_submission, ag_models.FeedbackCategory.max).total_points)

        counts_for_user_ultimate_submission = get_ultimate_submission(
            self.group, user=self.counts_for_user
        )
        self.assertEqual(best_submission, counts_for_user_ultimate_submission)

        does_not_count_for_user_ultimate_submission = get_ultimate_submission(
            self.group, user=self.does_not_count_for_user
        )
        self.assertEqual(other_submission, does_not_count_for_user_ultimate_submission)

    def test_no_submissions_count_for_user(self):
        oldest_submission = obj_build.make_finished_submission(
            self.group, does_not_count_for=[self.does_not_count_for_user.username]
        )
        most_recent_submission = obj_build.make_finished_submission(
            self.group, does_not_count_for=[self.does_not_count_for_user.username]
        )

        counts_for_user_ultimate_submission = get_ultimate_submission(
            self.group, user=self.counts_for_user
        )
        self.assertEqual(most_recent_submission, counts_for_user_ultimate_submission)

        does_not_count_for_user_ultimate_submission = get_ultimate_submission(
            self.group, user=self.does_not_count_for_user
        )
        self.assertIsNone(does_not_count_for_user_ultimate_submission)
