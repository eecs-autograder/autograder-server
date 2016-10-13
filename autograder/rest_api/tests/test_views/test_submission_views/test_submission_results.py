import datetime
from urllib.parse import urlencode

from django.core.urlresolvers import reverse
from django.utils import timezone

from rest_framework import status

import autograder.utils.testing.model_obj_builders as obj_build
from autograder.utils.testing import UnitTestBase
import autograder.rest_api.tests.test_views.common_generic_data as test_data
import autograder.rest_api.tests.test_views.common_test_impls as test_impls


def results_url(submission, feedback_type):
    url = reverse('submission-results-list',
                  kwargs={'submission_pk': submission.pk})
    url += '?' + urlencode({'feedback_type': feedback_type})
    return url


class _Shared:
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

    def build_all_results(self, submission):
        submission.results.all().delete()
        return [self.visible_to_students_result(submission),
                self.hidden_from_students_result(submission),
                self.visible_in_past_limit_result(submission),
                self.hidden_in_past_limit_result(submission),
                self.visible_in_ultimate_result(submission),
                self.hidden_in_ultimate_result(submission)]


class MiscListResultsTestCase(test_data.Client,
                              test_data.Project,
                              test_data.Submission,
                              test_impls.GetObjectTest,
                              UnitTestBase):
    def test_error_no_fdbk_type_query_param(self):
        self.client.force_authenticate(self.admin)
        submission = self.build_submission(self.admin_group(self.project))
        response = self.client.get(
            reverse('submission-results-list',
                    kwargs={'submission_pk': submission.pk}))
        self.assertEqual(status.HTTP_400_BAD_REQUEST, response.status_code)
        self.assertIn('feedback_type', response.data)

    def test_error_invalid_fdbk_type(self):
        self.client.force_authenticate(self.admin)
        submission = self.build_submission(self.admin_group(self.project))
        response = self.client.get(results_url(submission, 'not_a_type'))
        self.assertEqual(status.HTTP_400_BAD_REQUEST, response.status_code)
        self.assertIn('feedback_type', response.data)


class StaffListOwnResultsTestCase(_Shared,
                                  test_data.Client,
                                  test_data.Project,
                                  test_data.Submission,
                                  test_impls.GetObjectTest,
                                  UnitTestBase):
    def test_normal_fdbk_requested(self):
        group = self.staff_group(self.project)
        submission = self.build_submission(group)
        expected_results = [self.visible_to_students_result(submission)]
        all_results = expected_results + [self.hidden_from_students_result(submission)]
        self.do_list_results_test(submission, expected_results, all_results,
                                  'get_normal_feedback', 'normal')

    def test_past_limit_fdbk_requested(self):
        group = self.staff_group(self.project)
        submission = self.build_submission(group)
        self.assertFalse(submission.is_past_daily_limit)
        expected_results = [self.visible_in_past_limit_result(submission)]
        all_results = expected_results + [self.hidden_in_past_limit_result(submission)]
        self.do_list_results_test(
            submission, expected_results, all_results,
            'get_past_submission_limit_feedback', 'past_submission_limit')

    def test_ultimate_fdbk_requested(self):
        group = self.staff_group(self.project)
        submission = self.build_submission(group)
        # Force the other submission to be non-ultimate
        self.build_submission(group)
        self.assertNotEqual(group.ultimate_submission, submission)
        expected_results = [self.visible_in_ultimate_result(submission)]
        all_results = expected_results + [self.hidden_in_ultimate_result(submission)]
        self.do_list_results_test(
            submission, expected_results, all_results,
            'get_ultimate_submission_feedback', 'ultimate_submission')

    def test_staff_viewer_fdbk_requested(self):
        group = self.staff_group(self.project)
        submission = self.build_submission(group)
        results = [self.visible_to_students_result(submission),
                   self.hidden_from_students_result(submission),
                   self.visible_in_past_limit_result(submission),
                   self.hidden_in_past_limit_result(submission),
                   self.visible_in_ultimate_result(submission),
                   self.hidden_in_ultimate_result(submission)]
        self.do_list_results_test(submission, results, results,
                                  'get_staff_viewer_feedback', 'staff_viewer')

    def test_max_fdbk_requested(self):
        group = self.staff_group(self.project)
        submission = self.build_submission(group)
        results = [self.visible_to_students_result(submission),
                   self.hidden_from_students_result(submission),
                   self.visible_in_past_limit_result(submission),
                   self.hidden_in_past_limit_result(submission),
                   self.visible_in_ultimate_result(submission),
                   self.hidden_in_ultimate_result(submission)]
        self.do_list_results_test(submission, results, results,
                                  'get_max_feedback', 'max')


class StaffListStudentOrOtherStaffResultsTestCase(_Shared,
                                                  test_data.Client,
                                                  test_data.Project,
                                                  test_data.Submission,
                                                  test_impls.GetObjectTest,
                                                  UnitTestBase):
    def test_staff_viewer_fdbk_requested(self):
        for group in self.all_groups(self.visible_public_project):
            submission = self.build_submission(group)
            results = self.build_all_results(submission)
            for user in self.admin, self.staff:
                if group.members.filter(pk=user.pk).exists():
                    continue

                self.do_list_results_test(
                    submission, results, results,
                    'get_staff_viewer_feedback', 'staff_viewer',
                    user=user)

    def test_staff_viewer_fdbk_not_requested_permission_denied(self):
        for group in self.all_groups(self.visible_public_project):
            submission = self.build_submission(group)
            # Force the above submission to be non-ultimate
            self.build_submission(group)
            self.assertNotEqual(submission, group.ultimate_submission)

            for user in self.admin, self.staff:
                if group.members.filter(pk=user.pk).exists():
                    continue

                for feedback_type in ('normal', 'past_submission_limit',
                                      'ultimate_submission'):
                    self.do_permission_denied_get_test(
                        self.client, user, results_url(submission, feedback_type))

    def test_ultimate_submission_deadline_past_or_none_max_fdbk_requested(self):
        project = self.visible_public_project
        for group in self.all_groups(project):
            project.validate_and_update(
                visible_to_students=False,
                allow_submissions_from_non_enrolled_students=False)

            project.validate_and_update(
                closing_time=timezone.now() - datetime.timedelta(hours=1))
            self.do_max_fdbk_on_all_test(group)

            project.validate_and_update(closing_time=None)
            self.do_max_fdbk_on_all_test(group)

    def test_ultimate_submission_deadline_and_extension_past_max_fdbk_requested(self):
        project = self.visible_public_project
        project.validate_and_update(
            closing_time=timezone.now() - datetime.timedelta(hours=1))
        for group in self.all_groups(project):
            project.validate_and_update(
                visible_to_students=False,
                allow_submissions_from_non_enrolled_students=False)
            group.validate_and_update(extended_due_date=project.closing_time +
                                      datetime.timedelta(minutes=1))

    def do_max_fdbk_on_all_test(self, group):
        submission = self.build_submission(group)
        self.assertEqual(submission, group.ultimate_submission)
        results = self.build_all_results(submission)

        for user in self.admin, self.staff:
            if group.members.filter(pk=user.pk).exists():
                continue

            self.do_list_results_test(
                submission, results, results, 'get_max_feedback', 'max',
                user=user)

    def test_ultimate_submission_deadline_not_past_max_fdbk_forbidden(self):
        project = self.visible_public_project
        project.validate_and_update(
            closing_time=timezone.now() + datetime.timedelta(hours=1))
        for group in self.all_groups(project):
            self.do_max_fdbk_permission_denied_test(group)

    def test_ultimate_submission_extension_not_past_max_fdbk_forbidden(self):
        project = self.visible_public_project
        project.validate_and_update(
            closing_time=timezone.now() - datetime.timedelta(hours=1))
        for group in self.all_groups(project):
            # Make sure that the extension, not the closing time is
            # causing the 403
            self.do_max_fdbk_on_all_test(group)

            group.validate_and_update(extended_due_date=timezone.now() +
                                      datetime.timedelta(minutes=1))
            self.do_max_fdbk_permission_denied_test(group)

    def do_max_fdbk_permission_denied_test(self, group):
        submission = self.build_submission(group)
        self.assertEqual(submission, group.ultimate_submission)

        for user in self.admin, self.staff:
            if group.members.filter(pk=user.pk).exists():
                continue

            self.do_permission_denied_get_test(
                self.client, user, results_url(submission, 'max'))


class StudentListOwnResultsTestCase(_Shared,
                                    test_data.Client,
                                    test_data.Project,
                                    test_data.Submission,
                                    test_impls.GetObjectTest,
                                    UnitTestBase):
    def test_normal_fdbk_requested(self):
        self.fail()
        for project in self.visible_projects:
            group = self.enrolled_group(project)
            submission = self.non_ultimate_submission(group)
            results = [self.visible_to_students_result(submission),
                       self.hidden_from_students_result(submission)]
            self.do_list_results_test(submission, results[:1], results)

    def test_normal_fdbk_requested_submission_past_limit_permission_denied(self):
        # submission = self.past_limit_submission(group)
        # results = [self.visible_in_past_limit_result(submission),
        #            self.hidden_in_past_limit_result(submission)]
        # self.do_list_results_test(submission, results[:1], results)
        self.fail()

    def test_ultimate_fdbk_requested_deadline_none_or_past_and_submission_is_ultimate(self):
        # submission = self.most_recent_ultimate_submission(group)
        # submission.results.all().delete()
        # results = [self.visible_in_ultimate_result(submission),
        #            self.hidden_in_ultimate_result(submission)]
        # self.do_list_results_test(submission, results[:1], results)
        self.fail()

    def test_ultimate_fdbk_requested_extension_past_and_submission_is_ultimate(self):
        self.fail()

    def test_ultimate_fdbk_requested_deadline_not_past_permission_denied(self):
        self.fail()

    def test_ultimate_fdbk_requested_extension_not_past_permission_denied(self):
        self.fail()

    def test_ultimate_fdbk_requested_submission_not_ultimate_permission_denied(self):
        self.fail()

    def test_past_limit_fdbk_requested_submission_is_past_limit(self):
        self.fail()

    def test_past_limit_fdbk_requested_submission_not_past_limit_permission_denied(self):
        self.fail()

    def test_ultimate_fdbk_requested_submission_is_past_limit_and_ultimate(self):
        self.fail()

    # def test_non_enrolled_list_own_results(self):
    #     self.fail()
    #     group = self.non_enrolled_group(self.visible_public_project)
    #     submission = self.non_ultimate_submission(group)
    #     results = [self.visible_to_students_result(submission),
    #                self.hidden_from_students_result(submission)]
    #     self.do_list_results_test(submission, results[:1], results)

    #     submission = self.past_limit_submission(group)
    #     results = [self.visible_in_past_limit_result(submission),
    #                self.hidden_in_past_limit_result(submission)]
    #     self.do_list_results_test(submission, results[:1], results)

    #     group = self.non_enrolled_group(self.visible_public_project)
    #     submission = self.most_recent_ultimate_submission(group)
    #     submission.results.all().delete()
    #     results = [self.visible_in_ultimate_result(submission),
    #                self.hidden_in_ultimate_result(submission)]
    #     self.do_list_results_test(submission, results[:1], results)

    def test_max_fdbk_requested_permission_denied(self):
        self.fail()

    def test_staff_viewer_fdbk_requested_permission_denied(self):
        self.fail()

    def test_non_member_list_other_groups_results_permission_denied(self):
        self.fail()
        # group = self.enrolled_group(self.visible_public_project)
        # submission = self.non_ultimate_submission(group)
        # self.visible_to_students_result(submission)
        # self.visible_in_ultimate_result(submission)
        # self.visible_in_past_limit_result(submission)
        # other_user = self.clone_user(self.enrolled)
        # for user in other_user, self.nobody:
        #     self.do_permission_denied_get_test(
        #         self.client, user, results_url(submission))

    def test_project_hidden_permission_denied(self):
        self.fail()
        for project in self.hidden_projects:
            group = self.enrolled_group(project)
            submission = self.non_ultimate_submission(group)
            self.visible_to_students_result(submission)

            self.do_permission_denied_get_test(
                self.client, group.members.first(), results_url(submission))

    def test_non_enrolled_student_project_not_public_permission_denied(self):
        self.fail()

    # def test_non_enrolled_list_own_project_hidden_permission_denied(self):
    #     self.fail()
    #     group = self.non_enrolled_group(self.visible_public_project)
    #     submission = self.non_ultimate_submission(group)
    #     self.visible_public_project.validate_and_update(
    #         allow_submissions_from_non_enrolled_students=False)

    #     self.visible_to_students_result(submission)

    #     self.do_permission_denied_get_test(
    #         self.client, group.members.first(), results_url(submission))
