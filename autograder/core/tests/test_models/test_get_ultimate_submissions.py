import sys
from typing import List

import autograder.core.models as ag_models
import autograder.utils.testing.model_obj_builders as obj_build
from autograder.core.models.get_ultimate_submissions import (
    get_ultimate_submissions, get_ultimate_submission)
from autograder.core.submission_feedback import (
    update_denormalized_ag_test_results, AGTestPreLoader)
from autograder.utils.testing import UnitTestBase


class GetUltimateSubmissionsTestCase(UnitTestBase):
    def setUp(self):
        super().setUp()
        self.project = obj_build.make_project()

    def test_get_ultimate_for_single_group(self):
        data = self.prepare_data(self.project)
        group = data[0].group
        best_sub = data[0].best_submission
        most_recent = data[0].most_recent_submission

        print(group.submissions.count())
        print(group.submissions.all())

        self.assertEqual(ag_models.UltimateSubmissionPolicy.most_recent,
                         self.project.ultimate_submission_policy)
        [ultimate_most_recent] = get_ultimate_submissions(
            self.project, group, ag_test_preloader=AGTestPreLoader(self.project))
        self.assertEqual(most_recent, ultimate_most_recent.submission)

        self.project.validate_and_update(
            ultimate_submission_policy=ag_models.UltimateSubmissionPolicy.best)
        [ultimate_best] = get_ultimate_submissions(
            self.project, group, ag_test_preloader=AGTestPreLoader(self.project))
        self.assertEqual(best_sub, ultimate_best.submission)

    def test_get_ultimate_for_many_groups(self):
        data = self.prepare_data(self.project, num_groups=3)
        groups = [datum.group for datum in data]
        expected_most_recents = [datum.most_recent_submission for datum in data]
        expected_bests = [datum.best_submission for datum in data]

        self.assertEqual(ag_models.UltimateSubmissionPolicy.most_recent,
                         self.project.ultimate_submission_policy)
        ultimate_most_recents = get_ultimate_submissions(
            self.project, *groups, ag_test_preloader=AGTestPreLoader(self.project))
        self.assertCountEqual(
            expected_most_recents, [fdbk.submission for fdbk in ultimate_most_recents])

        self.project.validate_and_update(
            ultimate_submission_policy=ag_models.UltimateSubmissionPolicy.best)
        ultimate_bests = get_ultimate_submissions(
            self.project, *groups, ag_test_preloader=AGTestPreLoader(self.project))
        self.assertCountEqual(expected_bests, [fdbk.submission for fdbk in ultimate_bests])

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
                                          ag_test_preloader=AGTestPreLoader(self.project))])

    def test_get_ultimate_submission_group_has_no_submissions(self):
        for policy in ag_models.UltimateSubmissionPolicy:
            self.project.validate_and_update(ultimate_submission_policy=policy)
            group = obj_build.make_group(project=self.project)

            self.assertEqual(0, group.submissions.count())
            ultimate_submission = get_ultimate_submission(group)
            self.assertIsNone(ultimate_submission)

            ultimate_submissions = list(
                get_ultimate_submissions(
                    self.project, group, ag_test_preloader=AGTestPreLoader(self.project)))
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
