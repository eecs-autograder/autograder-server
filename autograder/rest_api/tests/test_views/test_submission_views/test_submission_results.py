from urllib.parse import urlencode

from django.core.urlresolvers import reverse

import autograder.core.tests.dummy_object_utils as obj_ut
from autograder.core.tests.temporary_filesystem_test_case import (
    TemporaryFilesystemTestCase)
import autograder.rest_api.tests.test_views.common_generic_data as test_data
import autograder.rest_api.tests.test_views.common_test_impls as test_impls


def results_url(submission, student_view=None):
    url = reverse('submission-results-list',
                  kwargs={'submission_pk': submission.pk})
    if student_view is not None:
        url += '?' + urlencode({'student_view': student_view})
    return url


class ListResultsTestCase(test_data.Client,
                          test_data.Project,
                          test_data.Submission,
                          test_impls.GetObjectTest,
                          TemporaryFilesystemTestCase):
    def test_staff_list_own_results_with_and_without_student_view(self):
        for project in self.all_projects:
            project_settings = project.to_dict(exclude_fields=['course'])
            project_settings.pop('pk')
            for group in self.staff_groups(project):
                submission = self.non_ultimate_submission(group)
                results = [self.visible_to_students_result(submission),
                           self.hidden_from_students_result(submission)]
                self.do_list_results_test(submission, results, results)
                self.do_list_results_test(submission, results[:1], results,
                                          student_view=True)

                submission = self.past_limit_submission(group)
                results = [self.visible_in_past_limit_result(submission),
                           self.hidden_in_past_limit_result(submission)]
                self.do_list_results_test(submission, results, results)
                self.do_list_results_test(submission, results[:1], results,
                                          student_view=True)

                submission = self.most_recent_ultimate_submission(group)
                submission.results.all().delete()
                results = [self.visible_in_ultimate_result(submission),
                           self.hidden_in_ultimate_result(submission)]
                self.do_list_results_test(submission, results, results)
                self.do_list_results_test(submission, results[:1], results,
                                          student_view=True)

                project.validate_and_update(**project_settings)

    def test_enrolled_list_own_results(self):
        for project in self.visible_projects:
            group = self.enrolled_group(project)
            submission = self.non_ultimate_submission(group)
            results = [self.visible_to_students_result(submission),
                       self.hidden_from_students_result(submission)]
            self.do_list_results_test(submission, results[:1], results)

            submission = self.past_limit_submission(group)
            results = [self.visible_in_past_limit_result(submission),
                       self.hidden_in_past_limit_result(submission)]
            self.do_list_results_test(submission, results[:1], results)

            submission = self.most_recent_ultimate_submission(group)
            submission.results.all().delete()
            results = [self.visible_in_ultimate_result(submission),
                       self.hidden_in_ultimate_result(submission)]
            self.do_list_results_test(submission, results[:1], results)

    def test_non_enrolled_list_own_results(self):
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

    def test_staff_list_other_all_shown(self):
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

    def test_non_member_list_other_permission_denied(self):
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
        for project in self.hidden_projects:
            group = self.enrolled_group(project)
            submission = self.non_ultimate_submission(group)
            self.visible_to_students_result(submission)

            self.do_permission_denied_get_test(
                self.client, group.members.first(), results_url(submission))

    def test_non_enrolled_list_own_project_hidden_permission_denied(self):
        group = self.non_enrolled_group(self.visible_public_project)
        submission = self.non_ultimate_submission(group)
        self.visible_public_project.validate_and_update(
            allow_submissions_from_non_enrolled_students=False)

        self.visible_to_students_result(submission)

        self.do_permission_denied_get_test(
            self.client, group.members.first(), results_url(submission))

    def do_list_results_test(self, submission, expected_result_objs,
                             all_result_objs, user=None, student_view=None):
        self.assertCountEqual(all_result_objs, submission.results.all())

        if user is None:
            user = submission.submission_group.members.first()

        expected_data = [
            result.get_feedback(user, student_view=student_view).to_dict()
            for result in expected_result_objs
        ]

        self.do_list_objects_test(
            self.client, user,
            results_url(submission, student_view=student_view), expected_data)

    def visible_to_students_result(self, submission):
        return obj_ut.build_compiled_ag_test_result(
            submission=submission, ag_test_kwargs={
                'visible_to_students': True,
            })

    def hidden_from_students_result(self, submission):
        return obj_ut.build_compiled_ag_test_result(
            submission=submission, ag_test_kwargs={
                'visible_to_students': False,
            })

    def visible_in_ultimate_result(self, submission):
        return obj_ut.build_compiled_ag_test_result(
            submission=submission, ag_test_kwargs={
                'visible_in_ultimate_submission': True,
            })

    def hidden_in_ultimate_result(self, submission):
        return obj_ut.build_compiled_ag_test_result(
            submission=submission, ag_test_kwargs={
                'visible_in_ultimate_submission': False,
            })

    def visible_in_past_limit_result(self, submission):
        return obj_ut.build_compiled_ag_test_result(
            submission=submission, ag_test_kwargs={
                'visible_in_past_limit_submission': True,
            })

    def hidden_in_past_limit_result(self, submission):
        return obj_ut.build_compiled_ag_test_result(
            submission=submission, ag_test_kwargs={
                'visible_in_past_limit_submission': False,
            })
