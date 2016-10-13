from urllib.parse import urlencode

from django.core.urlresolvers import reverse

import autograder.utils.testing.model_obj_builders as obj_build
from autograder.utils.testing import UnitTestBase
import autograder.rest_api.tests.test_views.common_generic_data as test_data
import autograder.rest_api.tests.test_views.common_test_impls as test_impls


def results_url(submission, feedback_type):
    url = reverse('submission-results-list',
                  kwargs={'submission_pk': submission.pk})
    url += '?' + urlencode({'feedback_type': feedback_type})
    return url


class ListResultsTestCase(test_data.Client,
                          test_data.Project,
                          test_data.Submission,
                          test_impls.GetObjectTest,
                          UnitTestBase):
    def test_error_no_fdbk_type_query_param(self):
        self.fail()

    def test_staff_list_own_normal_fdbk(self):
        group = self.staff_group(self.project)
        submission = self.build_submission(group)
        expected_results = [self.visible_to_students_result(submission)]
        all_results = expected_results + [self.hidden_from_students_result(submission)]
        self.do_list_results_test(submission, all_results, expected_results,
                                  'get_normal_feedback', 'normal')

    def test_staff_list_own_past_limit_fdbk(self):
        self.fail()
        for project in self.all_projects:
            group = self.staff_group(project)
            submission = self.past_limit_submission(group)
            results = [self.visible_to_students_result(submission),
                       self.visible_in_past_limit_result(submission),
                       self.hidden_from_students_result(submission),
                       self.hidden_in_past_limit_result(submission)]
            self.do_list_results_test(submission, results, results[2:],
                                      'get_past_submission_limit_feedback',
                                      'past_limit_submission')

    def test_staff_list_own_most_ultimate_fdbk(self):
        self.fail()
        for project in self.all_projects:
            group = self.staff_group(project)
            submission = self.most_recent_ultimate_submission(group)
            results = [self.visible_to_students_result(submission),
                       self.hidden_from_students_result(submission)]
            self.do_list_results_test(submission, results, results,
                                      'get_ultimate_submission_feedback',
                                      'ultimate_submission')

    def test_staff_list_own_staff_viewer_fdbk(self):
        self.fail()
        for project in self.all_projects:
            group = self.staff_group(project)
            for submission in (self.most_recent_ultimate_submission(group),
                               self.best_ultimate_submission(group)):
                submission = self.ultimate_submission(group)
                results = [self.visible_to_students_result(submission),
                           self.hidden_from_students_result(submission)]
                self.do_list_results_test(submission, results, results,
                                          'get_ultimate_submission_feedback',
                                          'ultimate_submission')
        self.fail()

    def test_staff_list_own_max_fdbk(self):
        self.fail()

    # def test_staff_list_own_results_all_fdbk_types(self):
    #     self.fail()
    #     for project in self.all_projects:
    #         project_settings = project.to_dict(exclude_fields=['course'])
    #         project_settings.pop('pk')
    #         for group in self.staff_groups(project):
    #             submission = self.non_ultimate_submission(group)
    #             results = [self.visible_to_students_result(submission),
    #                        self.hidden_from_students_result(submission)]
    #             self.do_list_results_test(submission, results, results,
    #                                       'get_normal_feedback', 'normal')
    #             self.do_list_results_test(submission, results[:1], results,
    #                                       'get_staff_viewer_feedback', 'staff_viewer')
    #             self.do_list_results_test(submission, results, results,
    #                                       'get_max_feedback', 'max')

    #             submission = self.past_limit_submission(group)
    #             results = [self.visible_in_past_limit_result(submission),
    #                        self.hidden_in_past_limit_result(submission)]
    #             self.do_list_results_test(
    #                 submission, results, results,
    #                 'get_past_submission_limit_feedback',
    #                 'past_limit_submission')
    #             self.do_list_results_test(submission, results[:1], results,
    #                                       student_view=True)

    #             submission = self.most_recent_ultimate_submission(group)
    #             submission.results.all().delete()
    #             results = [self.visible_in_ultimate_result(submission),
    #                        self.hidden_in_ultimate_result(submission)]
    #             self.do_list_results_test(submission, results, results)
    #             self.do_list_results_test(submission, results[:1], results,
    #                                       student_view=True)

    #             project.validate_and_update(**project_settings)

    def test_staff_list_other_all_results_shown_with_staff_viewer_fdbk(self):
        for group in self.all_groups(self.visible_public_project):
            submission = self.non_ultimate_submission(group)
            results = [
                self.visible_to_students_result(submission),
                self.hidden_from_students_result(submission),

                self.visible_in_past_limit_result(submission),
                self.hidden_in_past_limit_result(submission),

                self.visible_in_ultimate_result(submission),
                self.hidden_in_ultimate_result(submission),
            ]

            for user in self.admin, self.staff:
                if group.members.filter(pk=user.pk).exists():
                    continue

                self.do_list_results_test(
                    submission, results, results, user=user)
                self.do_list_results_test(
                    submission, results, results, user=user, student_view=True)

    def test_staff_list_other_ultimate_deadline_past_max_fdbk_requested(self):
        self.fail()

    def test_staff_list_other_ultimate_deadline_not_past_max_fdbk_requested_forbidden(self):
        self.fail()

    def test_staff_list_other_non_ultimate_max_fdbk_requested_permission_denied(self):
        self.fail()

    def test_staff_list_other_staff_viewer_not_requested_permission_denied(self):
        self.fail()

    def test_enrolled_list_own_results_normal_fdbk(self):
        self.fail()
        for project in self.visible_projects:
            group = self.enrolled_group(project)
            submission = self.non_ultimate_submission(group)
            results = [self.visible_to_students_result(submission),
                       self.hidden_from_students_result(submission)]
            self.do_list_results_test(submission, results[:1], results)

    def test_enrolled_list_own_results_normal_fdbk_submission_past_limit_permission_denied(self):
        # submission = self.past_limit_submission(group)
        # results = [self.visible_in_past_limit_result(submission),
        #            self.hidden_in_past_limit_result(submission)]
        # self.do_list_results_test(submission, results[:1], results)
        self.fail()

    def test_enrolled_list_own_results_ultimate_fdbk_ultimate_submission_past_deadline(self):
        # submission = self.most_recent_ultimate_submission(group)
        # submission.results.all().delete()
        # results = [self.visible_in_ultimate_result(submission),
        #            self.hidden_in_ultimate_result(submission)]
        # self.do_list_results_test(submission, results[:1], results)
        self.fail()

    def test_enrolled_list_own_results_ultimate_fdbk_deadline_not_past_permission_denied(self):
        self.fail()

    def test_enrolled_list_own_results_ultimate_fdbk_not_ultimate_subm_permission_denied(self):
        self.fail()

    def test_enrolled_list_own_results_past_limit_fdbk_subm_past_limit(self):
        self.fail()

    def test_enrolled_list_own_results_past_limit_fdbk_subm_not_past_limit_permission_denied(self):
        self.fail()

    def test_enrolled_list_own_ultimate_requested_submission_past_limit_and_ultimate(self):
        self.fail()

    def test_non_enrolled_list_own_results(self):
        self.fail()
        group = self.non_enrolled_group(self.visible_public_project)
        submission = self.non_ultimate_submission(group)
        results = [self.visible_to_students_result(submission),
                   self.hidden_from_students_result(submission)]
        self.do_list_results_test(submission, results[:1], results)

        submission = self.past_limit_submission(group)
        results = [self.visible_in_past_limit_result(submission),
                   self.hidden_in_past_limit_result(submission)]
        self.do_list_results_test(submission, results[:1], results)

        group = self.non_enrolled_group(self.visible_public_project)
        submission = self.most_recent_ultimate_submission(group)
        submission.results.all().delete()
        results = [self.visible_in_ultimate_result(submission),
                   self.hidden_in_ultimate_result(submission)]
        self.do_list_results_test(submission, results[:1], results)

    def test_non_staff_max_fdbk_requested_permission_denied(self):
        self.fail()

    def test_non_staff_non_member_member_list_other_permission_denied(self):
        self.fail()
        group = self.enrolled_group(self.visible_public_project)
        submission = self.non_ultimate_submission(group)
        self.visible_to_students_result(submission)
        self.visible_in_ultimate_result(submission)
        self.visible_in_past_limit_result(submission)
        other_user = self.clone_user(self.enrolled)
        for user in other_user, self.nobody:
            self.do_permission_denied_get_test(
                self.client, user, results_url(submission))

    def test_enrolled_list_own_project_hidden_permission_denied(self):
        self.fail()
        for project in self.hidden_projects:
            group = self.enrolled_group(project)
            submission = self.non_ultimate_submission(group)
            self.visible_to_students_result(submission)

            self.do_permission_denied_get_test(
                self.client, group.members.first(), results_url(submission))

    def test_non_enrolled_list_own_project_hidden_permission_denied(self):
        self.fail()
        group = self.non_enrolled_group(self.visible_public_project)
        submission = self.non_ultimate_submission(group)
        self.visible_public_project.validate_and_update(
            allow_submissions_from_non_enrolled_students=False)

        self.visible_to_students_result(submission)

        self.do_permission_denied_get_test(
            self.client, group.members.first(), results_url(submission))

    def do_list_results_test(self, submission, expected_result_objs,
                             all_result_objs, fdbk_python_method_name,
                             request_fdbk_type_str,
                             user=None):
        self.assertCountEqual(all_result_objs, submission.results.all())

        if user is None:
            user = submission.submission_group.members.first()

        expected_data = [
            getattr(result, fdbk_python_method_name)().to_dict()
            for result in expected_result_objs
        ]

        self.do_list_objects_test(
            self.client, user,
            results_url(submission, feedback_type=request_fdbk_type_str),
            expected_data)

    def visible_to_students_result(self, submission):
        return obj_build.build_compiled_ag_test_result(
            submission=submission, ag_test_kwargs={
                'visible_to_students': True,
                'feedback_configuration': obj_build.random_fdbk(),
                'staff_viewer_fdbk_conf': obj_build.random_fdbk()
            })

    def hidden_from_students_result(self, submission):
        return obj_build.build_compiled_ag_test_result(
            submission=submission, ag_test_kwargs={
                'visible_to_students': False,
                'feedback_configuration': obj_build.random_fdbk(),
                'staff_viewer_fdbk_conf': obj_build.random_fdbk()
            })

    def visible_in_ultimate_result(self, submission):
        return obj_build.build_compiled_ag_test_result(
            submission=submission, ag_test_kwargs={
                'visible_in_ultimate_submission': True,
                'ultimate_submission_fdbk_conf': obj_build.random_fdbk(),
                'staff_viewer_fdbk_conf': obj_build.random_fdbk()
            })

    def hidden_in_ultimate_result(self, submission):
        return obj_build.build_compiled_ag_test_result(
            submission=submission, ag_test_kwargs={
                'visible_in_ultimate_submission': False,
                'ultimate_submission_fdbk_conf': obj_build.random_fdbk(),
                'staff_viewer_fdbk_conf': obj_build.random_fdbk()
            })

    def visible_in_past_limit_result(self, submission):
        return obj_build.build_compiled_ag_test_result(
            submission=submission, ag_test_kwargs={
                'visible_in_past_limit_submission': True,
                'past_submission_limit_fdbk_conf': obj_build.random_fdbk(),
                'staff_viewer_fdbk_conf': obj_build.random_fdbk()
            })

    def hidden_in_past_limit_result(self, submission):
        return obj_build.build_compiled_ag_test_result(
            submission=submission, ag_test_kwargs={
                'visible_in_past_limit_submission': False,
                'past_submission_limit_fdbk_conf': obj_build.random_fdbk(),
                'staff_viewer_fdbk_conf': obj_build.random_fdbk()
            })
