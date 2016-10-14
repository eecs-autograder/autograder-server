import datetime
from urllib.parse import urlencode

from django.core.urlresolvers import reverse
from django.utils import timezone

from rest_framework import status

import autograder.utils.testing.model_obj_builders as obj_build
from autograder.utils.testing import UnitTestBase
import autograder.rest_api.tests.test_views.common_generic_data as test_data
import autograder.rest_api.tests.test_views.common_test_impls as test_impls


# IMPORTANT!!!!! Make sure that hide_ultimate_submission_fdbk is set to
# False for projects unless you need it to be True for a test case.
# do_list_results_test and do_permission_denied_list_results_test
# have a parameter that helps manage this.


def results_url(submission, feedback_type):
    url = reverse('submission-results-list',
                  kwargs={'submission_pk': submission.pk})
    url += '?' + urlencode({'feedback_type': feedback_type})
    return url


class _Shared:
    def do_list_results_test(self, submission, expected_result_objs,
                             all_result_objs, fdbk_python_method_name,
                             request_fdbk_type_str,
                             user=None, expected_hide_ultimate_fbdk=False):
        self.assertCountEqual(all_result_objs, submission.results.all())
        project = submission.submission_group.project
        if project.hide_ultimate_submission_fdbk != expected_hide_ultimate_fbdk:
            project.validate_and_update(
                hide_ultimate_submission_fdbk=expected_hide_ultimate_fbdk)
        self.assertEqual(
            expected_hide_ultimate_fbdk,
            submission.submission_group.project.hide_ultimate_submission_fdbk)

        if user is None:
            user = submission.submission_group.members.first()

        expected_data = [
            getattr(result, fdbk_python_method_name)().to_dict()
            for result in expected_result_objs
        ]

        response = self.do_list_objects_test(
            self.client, user,
            results_url(submission, feedback_type=request_fdbk_type_str),
            expected_data)
        return response

    def do_permission_denied_list_results_test(self, submission, user,
                                               request_fdbk_type_str,
                                               expected_hide_ultimate_fbdk=False):
        project = submission.submission_group.project
        if project.hide_ultimate_submission_fdbk != expected_hide_ultimate_fbdk:
            project.validate_and_update(
                hide_ultimate_submission_fdbk=expected_hide_ultimate_fbdk)

        self.assertEqual(
            expected_hide_ultimate_fbdk,
            submission.submission_group.project.hide_ultimate_submission_fdbk)

        self.do_permission_denied_get_test(
            self.client, user, results_url(submission, request_fdbk_type_str))

    def visible_to_students_result(self, submission):
        return obj_build.build_compiled_ag_test_result(
            submission=submission, ag_test_kwargs={
                'visible_to_students': True,
                'feedback_configuration': obj_build.random_fdbk(),
                'staff_viewer_fdbk_conf': obj_build.random_fdbk(),
                'visible_in_ultimate_submission': False
            })

    def hidden_from_students_result(self, submission):
        return obj_build.build_compiled_ag_test_result(
            submission=submission, ag_test_kwargs={
                'visible_to_students': False,
                'feedback_configuration': obj_build.random_fdbk(),
                'staff_viewer_fdbk_conf': obj_build.random_fdbk(),
                'visible_in_ultimate_submission': False
            })

    def visible_in_ultimate_result(self, submission):
        return obj_build.build_compiled_ag_test_result(
            submission=submission, ag_test_kwargs={
                'visible_in_ultimate_submission': True,
                'ultimate_submission_fdbk_conf': obj_build.random_fdbk(),
                'staff_viewer_fdbk_conf': obj_build.random_fdbk(),
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
                'staff_viewer_fdbk_conf': obj_build.random_fdbk(),
                'visible_in_ultimate_submission': False
            })

    def hidden_in_past_limit_result(self, submission):
        return obj_build.build_compiled_ag_test_result(
            submission=submission, ag_test_kwargs={
                'visible_in_past_limit_submission': False,
                'past_submission_limit_fdbk_conf': obj_build.random_fdbk(),
                'staff_viewer_fdbk_conf': obj_build.random_fdbk(),
                'visible_in_ultimate_submission': False
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

        # Staff should be able to see ultimate feedback even if it is
        # hidden
        self.assertTrue(group.project.hide_ultimate_submission_fdbk)

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
            user = self.staff
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

            user = self.staff
            if group.members.filter(pk=user.pk).exists():
                continue

            for feedback_type in ('normal', 'past_submission_limit',
                                  'ultimate_submission'):
                self.do_permission_denied_list_results_test(
                    submission, user, feedback_type)

    def test_ultimate_submission_deadline_past_or_none_max_fdbk_requested(self):
        project = self.visible_public_project

        # Staff should be able to see max feedback on ultimate
        # submissions even if it is hidden
        self.assertTrue(project.hide_ultimate_submission_fdbk)

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

            self.do_permission_denied_list_results_test(submission, user, 'max')


class StudentListOwnResultsTestCase(_Shared,
                                    test_data.Client,
                                    test_data.Project,
                                    test_data.Submission,
                                    test_impls.GetObjectTest,
                                    UnitTestBase):
    def test_normal_fdbk_requested(self):
        enrolled_submission = self.build_submission(
            self.enrolled_group(self.visible_private_project))
        non_enrolled_submission = self.build_submission(
            self.enrolled_group(self.visible_public_project))

        for submission in enrolled_submission, non_enrolled_submission:
            expected_results = [self.visible_to_students_result(submission)]
            all_results = expected_results + [self.hidden_from_students_result(submission)]

            self.do_list_results_test(
                submission, expected_results, all_results,
                'get_normal_feedback', 'normal')

    def test_normal_fdbk_requested_submission_past_limit_permission_denied(self):
        project = self.visible_private_project
        project.validate_and_update(submission_limit_per_day=1)

        for i in range(2):
            submission = self.build_submission(self.enrolled_group(project))

        self.assertTrue(submission.is_past_daily_limit)

        self.do_permission_denied_list_results_test(
            submission, submission.submission_group.members.first(), 'normal')

    def test_ultimate_fdbk_requested_deadline_and_extension_none_or_past_and_submission_is_ultimate(self):
        submission = self.build_submission(
            self.enrolled_group(self.visible_private_project))
        expected_results = [self.visible_in_ultimate_result(submission)]
        all_results = expected_results + [self.hidden_in_ultimate_result(submission)]

        for deadline in None, timezone.now() - datetime.timedelta(hours=1):
            group = submission.submission_group
            project = group.project
            project.validate_and_update(closing_time=deadline)

            for extension in None, timezone.now() - datetime.timedelta(minutes=1):
                group.validate_and_update(extended_due_date=extension)
                self.do_list_results_test(
                    submission, expected_results, all_results,
                    'get_ultimate_submission_feedback', 'ultimate_submission')

    def test_ultimate_fdbk_requested_deadline_or_extension_not_past_permission_denied(self):
        submission = self.build_submission(
            self.enrolled_group(self.visible_public_project))
        group = submission.submission_group
        project = group.project
        project.validate_and_update(
            closing_time=timezone.now() + datetime.timedelta(hours=1))
        self.do_permission_denied_list_results_test(
            submission, group.members.first(), 'ultimate_submission')

        project.validate_and_update(
            closing_time=timezone.now() - datetime.timedelta(hours=1))

        group.validate_and_update(
            extended_due_date=timezone.now() + datetime.timedelta(minutes=1))
        self.do_permission_denied_list_results_test(
            submission, group.members.first(), 'ultimate_submission')

    def test_ultimate_fdbk_requested_submission_not_ultimate_permission_denied(self):
        group = self.enrolled_group(self.visible_public_project)
        submission = self.build_submission(group)
        # Force the submission to be non-ultimate
        self.build_submission(group)
        self.assertNotEqual(submission, group.ultimate_submission)

        self.do_permission_denied_list_results_test(
            submission, group.members.first(), 'ultimate_submission')

    def test_ultimate_fdbk_requested_ultimate_fdbk_disabled_permission_denied(self):
        group = self.enrolled_group(self.visible_public_project)
        submission = self.build_submission(group)
        self.assertEqual(submission, group.ultimate_submission)

        self.do_list_results_test(
            submission, [], [], 'get_ultimate_submission_feedback',
            'ultimate_submission')

        group.project.validate_and_update(hide_ultimate_submission_fdbk=True)
        self.do_permission_denied_list_results_test(
            submission, group.members.first(), 'ultimate_submission',
            expected_hide_ultimate_fbdk=True)

    def test_past_limit_fdbk_requested_submission_is_past_limit(self):
        group = self.enrolled_group(self.visible_private_project)
        group.project.validate_and_update(submission_limit_per_day=1)
        for i in range(2):
            submission = self.build_submission(group)

        self.assertTrue(submission.is_past_daily_limit)
        expected_results = [self.visible_in_past_limit_result(submission)]
        all_results = expected_results + [self.hidden_in_past_limit_result(submission)]

        self.do_list_results_test(
            submission, expected_results, all_results,
            'get_past_submission_limit_feedback', 'past_submission_limit')

    def test_past_limit_fdbk_requested_submission_not_past_limit_permission_denied(self):
        group = self.enrolled_group(self.visible_private_project)
        group.project.validate_and_update(submission_limit_per_day=1)
        submission = self.build_submission(group)

        self.assertFalse(submission.is_past_daily_limit)

        self.do_permission_denied_list_results_test(
            submission, group.members.first(), 'past_submission_limit')

    def test_ultimate_fdbk_requested_submission_is_past_limit_and_ultimate(self):
        self.maxDiff = None
        group = self.enrolled_group(self.visible_private_project)
        group.project.validate_and_update(submission_limit_per_day=1)
        for i in range(2):
            submission = self.build_submission(group)

        self.assertTrue(submission.is_past_daily_limit)
        self.assertEqual(submission, group.ultimate_submission)

        expected_results = [self.visible_in_ultimate_result(submission)]
        all_results = expected_results + [
            self.hidden_in_ultimate_result(submission),
            self.visible_in_past_limit_result(submission),
            self.hidden_in_past_limit_result(submission)
        ]

        self.do_list_results_test(
            submission, expected_results, all_results,
            'get_ultimate_submission_feedback', 'ultimate_submission')

    def test_max_fdbk_requested_permission_denied(self):
        submission = self.build_submission(
            self.enrolled_group(self.visible_public_project))
        self.do_permission_denied_list_results_test(
            submission, submission.submission_group.members.first(), 'max')

    def test_staff_viewer_fdbk_requested_permission_denied(self):
        submission = self.build_submission(
            self.enrolled_group(self.visible_public_project))
        self.do_permission_denied_list_results_test(
            submission, submission.submission_group.members.first(), 'staff_viewer')

    def test_non_member_list_other_groups_results_permission_denied(self):
        group = self.enrolled_group(self.visible_public_project)
        submission = self.build_submission(group)
        other_user = self.clone_user(self.enrolled)
        for user in other_user, self.nobody:
            self.do_permission_denied_list_results_test(submission, user, 'normal')

    def test_project_hidden_permission_denied(self):
        for project in self.hidden_projects:
            group = self.enrolled_group(project)
            submission = self.build_submission(group)
            self.do_permission_denied_list_results_test(submission, group.members.first(), 'normal')

    def test_non_enrolled_student_project_not_public_permission_denied(self):
        project = self.visible_public_project
        group = self.non_enrolled_group(project)
        submission = self.build_submission(group)
        project.validate_and_update(
            allow_submissions_from_non_enrolled_students=False)

        self.do_permission_denied_list_results_test(submission, group.members.first(), 'normal')
