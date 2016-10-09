from django.utils import timezone

from autograder.core.models.autograder_test_case.feedback_config import (
    FeedbackConfig)

from autograder.utils.testing import UnitTestBase
import autograder.utils.testing.model_obj_builders as obj_build
import autograder.utils.testing.generic_data as gen_data


class GetFeedbackNormalSubmissionTestCase(gen_data.Project,
                                          gen_data.Submission,
                                          UnitTestBase):
    def setUp(self):
        super().setUp()
        self.fdbk = obj_build.random_fdbk()
        # self.maxDiff = None

    def test_staff_get_own_max_fdbk(self):
        for group in self.staff_groups(self.project):
            submission = self.non_ultimate_submission(group)
            result = obj_build.build_compiled_ag_test_result(
                submission=submission,
                ag_test_kwargs={'feedback_configuration': self.fdbk})
            ag_test = result.test_case

            self.assertEqual(self.project, ag_test.project)
            actual_fdbk = result.get_feedback(group.members.first()).to_dict()

            ag_test.validate_and_update(
                feedback_configuration=FeedbackConfig.create_with_max_fdbk())
            self.assertEqual(result.get_feedback().to_dict(), actual_fdbk)

            ag_test.delete()

    def test_student_get_own_normal_fdbk(self):
        for group in self.non_staff_groups(self.visible_public_project):
            submission = self.non_ultimate_submission(group)
            result = obj_build.build_compiled_ag_test_result(
                submission=submission,
                ag_test_kwargs={'feedback_configuration': self.fdbk})

            actual_fdbk = result.get_feedback(group.members.first()).to_dict()
            self.assertEqual(result.get_feedback().to_dict(), actual_fdbk)

            result.test_case.delete()

    def test_staff_get_other_staff_viewer_fdbk(self):
        for group in self.all_groups(self.visible_public_project):
            for user in self.admin, self.staff:
                if group.members.filter(pk=user.pk).exists():
                    continue

                submission = self.non_ultimate_submission(group)
                result = obj_build.build_compiled_ag_test_result(
                    submission=submission,
                    ag_test_kwargs={'staff_viewer_fdbk_conf': self.fdbk})
                ag_test = result.test_case

                actual_fdbk = result.get_feedback(user).to_dict()
                ag_test.validate_and_update(feedback_configuration=self.fdbk)
                self.assertEqual(result.get_feedback().to_dict(), actual_fdbk)

                ag_test.delete()

    def test_staff_get_own_with_student_view(self):
        for group in self.staff_groups(self.project):
            submission = self.non_ultimate_submission(group)
            result = obj_build.build_compiled_ag_test_result(
                submission=submission,
                ag_test_kwargs={'feedback_configuration': self.fdbk})

            actual_fdbk = result.get_feedback(
                group.members.first(), student_view=True).to_dict()
            self.assertEqual(result.get_feedback().to_dict(), actual_fdbk)

            result.test_case.delete()

    def test_staff_get_other_with_student_view(self):
        for group in self.all_groups(self.visible_public_project):
            for user in self.admin, self.staff:
                if group.members.filter(pk=user.pk).exists():
                    continue

                submission = self.non_ultimate_submission(group)
                result = obj_build.build_compiled_ag_test_result(
                    submission=submission,
                    ag_test_kwargs={'staff_viewer_fdbk_conf': self.fdbk})
                ag_test = result.test_case

                actual_fdbk = result.get_feedback(
                    user, student_view=True).to_dict()

                # Making sure staff gets student view (normal) feedback
                # instead of staff viewer
                self.assertEqual(result.get_feedback().to_dict(), actual_fdbk)

                ag_test.delete()


class GetFeedbackUltimateSubmissionTestCase(gen_data.Project,
                                            gen_data.Submission,
                                            UnitTestBase):
    def setUp(self):
        super().setUp()
        self.fdbk = obj_build.random_fdbk()
        # self.maxDiff = None

    def test_admin_or_staff_get_own_max_fdbk(self):
        for group in self.staff_groups(self.project):
            submission = self.best_ultimate_submission(group)
            result = obj_build.build_compiled_ag_test_result(
                submission=submission,
                ag_test_kwargs={'ultimate_submission_fdbk_conf': self.fdbk})
            ag_test = result.test_case

            actual_fdbk = result.get_feedback(group.members.first()).to_dict()

            ag_test.validate_and_update(
                feedback_configuration=FeedbackConfig.create_with_max_fdbk())
            self.assertEqual(result.get_feedback().to_dict(), actual_fdbk)

            ag_test.delete()

    def test_student_get_own_ultimate_fdbk(self):
        '''
        Checks all types of ultimate submissions and makes sure
        that being an ultimate submission overrides being past the
        daily limit.
        '''
        submission_funcs = [self.best_ultimate_submission,
                            self.most_recent_ultimate_submission,
                            self.past_limit_most_recent_ultimate_submission,
                            self.past_limit_best_ultimate_submission]
        for group in self.non_staff_groups(self.visible_public_project):
            for submission_func in submission_funcs:
                submission = submission_func(group)
                self.assertEqual(submission, group.ultimate_submission)
                result = obj_build.build_compiled_ag_test_result(
                    submission=submission,
                    ag_test_kwargs={
                        'ultimate_submission_fdbk_conf': self.fdbk})
                ag_test = result.test_case

                actual_fdbk = (
                    result.get_feedback(group.members.first()).to_dict())

                ag_test.validate_and_update(feedback_configuration=self.fdbk)
                self.assertEqual(result.get_feedback().to_dict(), actual_fdbk)

                ag_test.delete()
                submission.delete()

    def test_ultimate_hidden_student_get_own_normal_fdbk(self):
        for group in self.non_staff_groups(self.visible_public_project):
            submission = self.most_recent_ultimate_submission(group)
            self.assertEqual(submission, group.ultimate_submission)
            result = obj_build.build_compiled_ag_test_result(
                submission=submission,
                ag_test_kwargs={'ultimate_submission_fdbk_conf': self.fdbk})

            self.visible_public_project.validate_and_update(
                hide_ultimate_submission_fdbk=True)

            actual_fdbk = result.get_feedback(group.members.first()).to_dict()
            self.assertEqual(result.get_feedback().to_dict(), actual_fdbk)

            result.test_case.delete()

    def test_deadline_not_past_student_get_own_normal_fdbk(self):
        for group in self.non_staff_groups(self.visible_public_project):
            submission = self.most_recent_ultimate_submission(group)
            self.assertEqual(submission, group.ultimate_submission)
            result = obj_build.build_compiled_ag_test_result(
                submission=submission,
                ag_test_kwargs={'ultimate_submission_fdbk_conf': self.fdbk})

            self.visible_public_project.validate_and_update(
                closing_time=timezone.now() + timezone.timedelta(minutes=5))

            actual_fdbk = result.get_feedback(group.members.first()).to_dict()
            self.assertEqual(result.get_feedback().to_dict(), actual_fdbk)

            result.test_case.delete()

    def test_staff_get_other_staff_viewer_fdbk(self):
        for group in self.all_groups(self.visible_public_project):
            for user in self.admin, self.staff:
                if group.members.filter(pk=user.pk).exists():
                    continue

                submission = self.best_ultimate_submission(group)
                self.assertEqual(submission, group.ultimate_submission)
                result = obj_build.build_compiled_ag_test_result(
                    submission=submission,
                    ag_test_kwargs={'staff_viewer_fdbk_conf': self.fdbk})
                ag_test = result.test_case

                actual_fdbk = result.get_feedback(user).to_dict()
                ag_test.validate_and_update(feedback_configuration=self.fdbk)
                self.assertEqual(result.get_feedback().to_dict(), actual_fdbk)

                ag_test.delete()

    def test_staff_get_own_with_student_view(self):
        submission_funcs = [self.best_ultimate_submission,
                            self.most_recent_ultimate_submission,
                            self.past_limit_most_recent_ultimate_submission,
                            self.past_limit_best_ultimate_submission]
        for group in self.staff_groups(self.project):
            for submission_func in submission_funcs:
                submission = submission_func(group)
                self.assertEqual(submission, group.ultimate_submission)
                result = obj_build.build_compiled_ag_test_result(
                    submission=submission,
                    ag_test_kwargs={
                        'ultimate_submission_fdbk_conf': self.fdbk})
                ag_test = result.test_case

                actual_fdbk = result.get_feedback(
                    group.members.first(), student_view=True).to_dict()

                ag_test.validate_and_update(feedback_configuration=self.fdbk)
                self.assertEqual(result.get_feedback().to_dict(), actual_fdbk)

                ag_test.delete()
                submission.delete()


class GetFeedbackPastLimitSubmissionTestCase(gen_data.Project,
                                             gen_data.Submission,
                                             UnitTestBase):
    def setUp(self):
        super().setUp()
        self.fdbk = obj_build.random_fdbk()
        # self.maxDiff = None

    def test_admin_or_staff_get_own_max_fdbk(self):
        for group in self.staff_groups(self.project):
            submission = self.past_limit_most_recent_submission(group)
            self.assertTrue(submission.is_past_daily_limit)
            result = obj_build.build_compiled_ag_test_result(
                submission=submission,
                ag_test_kwargs={'past_submission_limit_fdbk_conf': self.fdbk})
            ag_test = result.test_case

            self.assertEqual(self.project, ag_test.project)
            actual_fdbk = result.get_feedback(group.members.first()).to_dict()

            ag_test.validate_and_update(
                feedback_configuration=FeedbackConfig.create_with_max_fdbk())
            self.assertEqual(result.get_feedback().to_dict(), actual_fdbk)

            ag_test.delete()

    def test_student_get_own_past_limit_fbdk(self):
        for group in self.non_staff_groups(self.visible_public_project):
            submission = self.past_limit_most_recent_submission(group)
            self.assertTrue(submission.is_past_daily_limit)
            result = obj_build.build_compiled_ag_test_result(
                submission=submission,
                ag_test_kwargs={'past_submission_limit_fdbk_conf': self.fdbk})
            ag_test = result.test_case

            actual_fdbk = result.get_feedback(group.members.first()).to_dict()
            ag_test.validate_and_update(feedback_configuration=self.fdbk)
            self.assertEqual(result.get_feedback().to_dict(), actual_fdbk)

            ag_test.delete()

    def test_student_get_own_ultimate_past_limit_ultimate_hidden(self):
        for group in self.non_staff_groups(self.visible_public_project):
            submission = self.past_limit_best_ultimate_submission(group)
            self.assertTrue(submission.is_past_daily_limit)
            self.assertEqual(submission, group.ultimate_submission)
            self.assertTrue(submission.is_past_daily_limit)
            result = obj_build.build_compiled_ag_test_result(
                submission=submission,
                ag_test_kwargs={'past_submission_limit_fdbk_conf': self.fdbk})
            ag_test = result.test_case

            self.visible_public_project.validate_and_update(
                hide_ultimate_submission_fdbk=True)

            actual_fdbk = result.get_feedback(group.members.first()).to_dict()
            ag_test.validate_and_update(feedback_configuration=self.fdbk)
            self.assertEqual(result.get_feedback().to_dict(), actual_fdbk)

            ag_test.delete()

    def test_student_get_own_ultimate_past_limit_deadline_not_past(self):
        for group in self.non_staff_groups(self.visible_public_project):
            submission = self.past_limit_most_recent_ultimate_submission(group)
            self.assertTrue(submission.is_past_daily_limit)
            self.assertEqual(submission, group.ultimate_submission)
            result = obj_build.build_compiled_ag_test_result(
                submission=submission,
                ag_test_kwargs={'past_submission_limit_fdbk_conf': self.fdbk})
            ag_test = result.test_case

            self.visible_public_project.validate_and_update(
                closing_time=timezone.now() + timezone.timedelta(minutes=5))

            actual_fdbk = result.get_feedback(group.members.first()).to_dict()
            ag_test.validate_and_update(feedback_configuration=self.fdbk)
            self.assertEqual(result.get_feedback().to_dict(), actual_fdbk)

            ag_test.delete()

    def test_staff_get_other_staff_viewer_fdbk(self):
        for group in self.staff_groups(self.project):
            submission = self.past_limit_most_recent_submission(group)
            self.assertTrue(submission.is_past_daily_limit)
            result = obj_build.build_compiled_ag_test_result(
                submission=submission,
                ag_test_kwargs={'past_submission_limit_fdbk_conf': self.fdbk})
            ag_test = result.test_case

            actual_fdbk = result.get_feedback(
                group.members.first(), student_view=True).to_dict()
            ag_test.validate_and_update(feedback_configuration=self.fdbk)
            self.assertEqual(result.get_feedback().to_dict(), actual_fdbk)

            ag_test.delete()
