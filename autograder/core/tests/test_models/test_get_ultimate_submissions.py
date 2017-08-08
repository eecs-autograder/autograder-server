import sys
from typing import List

import autograder.core.models as ag_models
from autograder.core.models.get_ultimate_submissions import get_ultimate_submissions

from autograder.utils.testing import UnitTestBase, Timer
import autograder.utils.testing.model_obj_builders as obj_build


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
        [ultimate_most_recent] = get_ultimate_submissions(self.project, group.pk)
        self.assertEqual(most_recent, ultimate_most_recent)

        self.project.validate_and_update(
            ultimate_submission_policy=ag_models.UltimateSubmissionPolicy.best)
        [ultimate_best] = get_ultimate_submissions(self.project, group.pk)
        self.assertEqual(best_sub, ultimate_best)

    def test_get_ultimate_for_many_groups(self):
        data = self.prepare_data(self.project, num_groups=3)
        group_pks = [datum.group.pk for datum in data]
        expected_most_recents = [datum.most_recent_submission for datum in data]
        expected_bests = [datum.best_submission for datum in data]

        self.assertEqual(ag_models.UltimateSubmissionPolicy.most_recent,
                         self.project.ultimate_submission_policy)
        ultimate_most_recents = get_ultimate_submissions(self.project, *group_pks)
        self.assertCountEqual(expected_most_recents, ultimate_most_recents)

        self.project.validate_and_update(
            ultimate_submission_policy=ag_models.UltimateSubmissionPolicy.best)
        ultimate_bests = get_ultimate_submissions(self.project, *group_pks)
        self.assertCountEqual(expected_bests, ultimate_bests)

    def test_get_ultimate_only_finished_grading_status_considered(self):
        group = obj_build.make_group(project=self.project)
        ultimate_submission = obj_build.build_finished_submission(submission_group=group)
        non_considered_statuses = filter(
            lambda val: val != ag_models.Submission.GradingStatus.finished_grading,
            ag_models.Submission.GradingStatus.values)
        for grading_status in non_considered_statuses:
            obj_build.build_submission(submission_group=group, status=grading_status)

        self.assertEqual(
            1,
            ag_models.Submission.objects.filter(
                status=ag_models.Submission.GradingStatus.finished_grading).count())

        for ultimate_submission_policy in ag_models.UltimateSubmissionPolicy:
            self.project.validate_and_update(ultimate_submission_policy=ultimate_submission_policy)
            self.assertSequenceEqual([ultimate_submission],
                                     list(get_ultimate_submissions(self.project)))

    class GroupAndSubmissionData:
        def __init__(self, group: ag_models.SubmissionGroup,
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
            best_sub = obj_build.build_finished_submission(submission_group=group)
            for cmd in cmds:
                obj_build.make_correct_ag_test_command_result(cmd, submission=best_sub)

            for j in range(num_other_submissions):
                sub = obj_build.build_finished_submission(submission_group=group)
                for cmd in cmds:
                    obj_build.make_incorrect_ag_test_command_result(cmd, submission=sub)

            most_recent = obj_build.build_finished_submission(submission_group=group)
            for cmd in cmds:
                obj_build.make_incorrect_ag_test_command_result(cmd, submission=most_recent)

            group_and_submission_data.append(
                self.GroupAndSubmissionData(group, best_sub, most_recent))

        return group_and_submission_data
