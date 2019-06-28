import datetime
import json

from django.urls import reverse
from django.utils import timezone
from rest_framework import status
from rest_framework.test import APIClient

import autograder.core.models as ag_models
import autograder.utils.testing.model_obj_builders as obj_build
from autograder.core.submission_feedback import update_denormalized_ag_test_results
from autograder.core.tests.test_submission_feedback.fdbk_getter_shortcuts import get_suite_fdbk
from autograder.utils.testing import UnitTestBase

from .get_output_and_diff_test_urls import get_output_and_diff_test_urls


class _SetUp(UnitTestBase):
    def setUp(self):
        super().setUp()

        self.client = APIClient()

        self.ag_test_cmd = obj_build.make_full_ag_test_command()

        self.ag_test_case = self.ag_test_cmd.ag_test_case
        self.ag_test_suite = self.ag_test_case.ag_test_suite
        self.project = self.ag_test_suite.project
        self.project.validate_and_update(
            visible_to_students=True,
            hide_ultimate_submission_fdbk=False,
            closing_time=timezone.now() + datetime.timedelta(days=1)
        )
        self.course = self.project.course

        self.student_group1 = obj_build.make_group(project=self.project)
        self.student1 = self.student_group1.members.first()

        self.student_group_normal_submission = obj_build.make_finished_submission(
            group=self.student_group1)
        self.normal_submission_result = obj_build.make_correct_ag_test_command_result(
            self.ag_test_cmd, submission=self.student_group_normal_submission)
        self.student_group_normal_submission = update_denormalized_ag_test_results(
            self.student_group_normal_submission.pk)

        staff_group = obj_build.make_group(
            project=self.project, members_role=obj_build.UserRole.staff)
        self.staff = staff_group.members.first()

        self.staff_submission = obj_build.make_finished_submission(group=staff_group)
        self.staff_result = obj_build.make_correct_ag_test_command_result(
            self.ag_test_cmd, submission=self.staff_submission)
        self.staff_submission = update_denormalized_ag_test_results(self.staff_submission.pk)


class AGTestSuiteOutputFeedbackTestCase(_SetUp):
    def test_get_suite_result_setup_output_visible(self):
        self.assertTrue(self.ag_test_suite.normal_fdbk_config.show_setup_stdout)
        self.assertTrue(self.ag_test_suite.normal_fdbk_config.show_setup_stderr)
        self.assertTrue(self.ag_test_suite.normal_fdbk_config.visible)

        self.client.force_authenticate(self.student1)

        suite_res = self.normal_submission_result.ag_test_case_result.ag_test_suite_result
        self._do_suite_result_output_test(self.client, suite_res.submission, suite_res,
                                          ag_models.FeedbackCategory.normal)

    def test_get_suite_result_setup_output_hidden(self):
        self.ag_test_suite.validate_and_update(normal_fdbk_config={'show_setup_stdout': False})
        self.ag_test_suite.validate_and_update(normal_fdbk_config={'show_setup_stderr': False})
        self.assertTrue(self.ag_test_suite.normal_fdbk_config.visible)

        self.client.force_authenticate(self.student1)

        suite_res = self.normal_submission_result.ag_test_case_result.ag_test_suite_result
        self._do_suite_result_output_test(self.client, suite_res.submission, suite_res,
                                          ag_models.FeedbackCategory.normal)

    def test_suite_result_output_requested_on_not_visible_suite(self):
        self.ag_test_suite.validate_and_update(normal_fdbk_config={'visible': False})
        self.assertTrue(self.ag_test_suite.normal_fdbk_config.show_setup_stdout)
        self.assertTrue(self.ag_test_suite.normal_fdbk_config.show_setup_stderr)

        self.client.force_authenticate(self.student1)

        suite_res = self.normal_submission_result.ag_test_case_result.ag_test_suite_result
        self._do_suite_result_output_test(self.client, suite_res.submission, suite_res,
                                          ag_models.FeedbackCategory.normal)

    def test_suite_result_output_requested_suite_doesnt_exist_404(self):
        self.client.force_authenticate(self.staff)

        suite_result = self.staff_result.ag_test_case_result.ag_test_suite_result

        with suite_result.open_setup_stdout('w') as f:
            f.write('weee')
        with suite_result.open_setup_stderr('w') as f:
            f.write('wooo')

        field_names = ['setup_stdout', 'setup_stderr']
        url_lookups = [
            'ag-test-suite-result-stdout',
            'ag-test-suite-result-stderr'
        ]

        suite_result_pk = suite_result.pk
        self.ag_test_suite.delete()

        url_kwargs = {
            'pk': self.staff_submission.pk,
            'result_pk': suite_result_pk
        }

        url_query_str = f'?feedback_category={ag_models.FeedbackCategory.max.value}'

        for field_name, url_lookup in zip(field_names, url_lookups):
            url = reverse(url_lookup, kwargs=url_kwargs) + url_query_str
            response = self.client.get(url)
            self.assertEqual(status.HTTP_404_NOT_FOUND, response.status_code)

        url = reverse('ag-test-suite-result-output-size', kwargs=url_kwargs) + url_query_str
        response = self.client.get(url)
        self.assertEqual(status.HTTP_404_NOT_FOUND, response.status_code)

    def _do_suite_result_output_test(self, client, submission, suite_result, fdbk_category):
        with suite_result.open_setup_stdout('w') as f:
            f.write('adkjfaksdjf;akjsdf;')
        with suite_result.open_setup_stderr('w') as f:
            f.write('qewiruqpewpuir')

        fdbk = get_suite_fdbk(suite_result, fdbk_category)

        field_names = ['setup_stdout', 'setup_stderr']
        url_lookups = [
            'ag-test-suite-result-stdout',
            'ag-test-suite-result-stderr'
        ]
        url_kwargs = {'pk': submission.pk, 'result_pk': suite_result.pk}
        url_query_str = '?feedback_category={}'.format(fdbk_category.value)
        for field_name, url_lookup in zip(field_names, url_lookups):
            print(url_lookup)
            url = reverse(url_lookup, kwargs=url_kwargs) + url_query_str
            response = client.get(url)

            expected = getattr(fdbk, field_name)
            if expected is None or not fdbk.fdbk_conf.visible:
                self.assertIsNone(response.data)
            else:
                self.assertEqual(expected.read(),
                                 b''.join((chunk for chunk in response.streaming_content)))

        # Output size endpoint
        url = reverse('ag-test-suite-result-output-size', kwargs=url_kwargs) + url_query_str
        response = client.get(url)

        if not fdbk.fdbk_conf.visible:
            self.assertIsNone(response.data)
        else:
            expected = {
                'setup_stdout_size': fdbk.get_setup_stdout_size(),
                'setup_stderr_size': fdbk.get_setup_stderr_size(),
            }
            self.assertEqual(expected, response.data)


class AGTestCommandOutputFeedbackTestCase(_SetUp):
    def test_cmd_result_output_or_diff_requested_on_cmd_in_not_visible_suite(self):
        self.ag_test_suite.validate_and_update(normal_fdbk_config={'visible': False})
        self.client.force_authenticate(self.student1)
        self.do_get_output_and_diff_on_hidden_ag_test_test(
            self.client, self.student_group_normal_submission,
            self.normal_submission_result, ag_models.FeedbackCategory.normal)

    def test_cmd_result_output_or_diff_requested_on_cmd_in_not_visible_case(self):
        self.ag_test_case.validate_and_update(normal_fdbk_config={'visible': False})
        self.client.force_authenticate(self.student1)
        self.do_get_output_and_diff_on_hidden_ag_test_test(
            self.client, self.student_group_normal_submission,
            self.normal_submission_result, ag_models.FeedbackCategory.normal)

    def test_cmd_result_output_or_diff_requested_on_not_visible_cmd(self):
        self.ag_test_cmd.validate_and_update(normal_fdbk_config={'visible': False})
        self.client.force_authenticate(self.student1)
        self.do_get_output_and_diff_on_hidden_ag_test_test(
            self.client, self.student_group_normal_submission,
            self.normal_submission_result, ag_models.FeedbackCategory.normal)

    def test_cmd_result_output_or_diff_requested_individual_cmds_not_shown(self):
        self.ag_test_case.validate_and_update(
            normal_fdbk_config={'show_individual_commands': False})
        self.client.force_authenticate(self.student1)
        self.do_get_output_and_diff_on_hidden_ag_test_test(
            self.client, self.student_group_normal_submission,
            self.normal_submission_result, ag_models.FeedbackCategory.normal)

    def test_cmd_result_output_or_diff_requested_individual_cases_not_shown(self):
        self.ag_test_suite.validate_and_update(normal_fdbk_config={'show_individual_tests': False})
        self.client.force_authenticate(self.student1)
        self.do_get_output_and_diff_on_hidden_ag_test_test(
            self.client, self.student_group_normal_submission,
            self.normal_submission_result, ag_models.FeedbackCategory.normal)

    def test_cmd_diff_with_non_utf_chars(self):
        non_utf_bytes = b'\x80 and some other stuff just because\n'
        output = 'some stuff'
        self.ag_test_cmd.validate_and_update(
            expected_stdout_source=ag_models.ExpectedOutputSource.text,
            expected_stdout_text=output,
            expected_stderr_source=ag_models.ExpectedOutputSource.text,
            expected_stderr_text=output,
        )
        with open(self.staff_result.stdout_filename, 'wb') as f:
            f.write(non_utf_bytes)
        with open(self.staff_result.stderr_filename, 'wb') as f:
            f.write(non_utf_bytes)

        self.client.force_authenticate(self.staff)
        url = (reverse('ag-test-cmd-result-stdout-diff',
                       kwargs={'pk': self.staff_submission.pk,
                               'result_pk': self.staff_result.pk})
               + '?feedback_category=max')

        expected_diff = ['- ' + output, '+ ' + non_utf_bytes.decode('utf-8', 'surrogateescape')]
        response = self.client.get(url)
        self.assertEqual(status.HTTP_200_OK, response.status_code)
        self.assertEqual(expected_diff, json.loads(response.content.decode('utf-8')))

        url = (reverse('ag-test-cmd-result-stderr-diff',
                       kwargs={'pk': self.staff_submission.pk,
                               'result_pk': self.staff_result.pk})
               + '?feedback_category=max')
        response = self.client.get(url)
        self.assertEqual(status.HTTP_200_OK, response.status_code)
        self.assertEqual(expected_diff, json.loads(response.content.decode('utf-8')))

    def test_cmd_result_output_or_diff_requested_cmd_doesnt_exist_404(self):
        urls_and_field_names = get_output_and_diff_test_urls(
            self.staff_submission,
            self.staff_result,
            ag_models.FeedbackCategory.max)

        self.ag_test_cmd.delete()

        self.client.force_authenticate(self.staff)
        for url, field_name in urls_and_field_names:
            response = self.client.get(url)
            self.assertEqual(status.HTTP_404_NOT_FOUND, response.status_code)

    def do_get_output_and_diff_on_hidden_ag_test_test(self, client,
                                                      submission: ag_models.Submission,
                                                      cmd_result: ag_models.AGTestCommandResult,
                                                      fdbk_category: ag_models.FeedbackCategory):
        urls_and_field_names = get_output_and_diff_test_urls(
            submission, cmd_result, fdbk_category)
        for url, field_name in urls_and_field_names:
            response = client.get(url)
            self.assertEqual(status.HTTP_200_OK, response.status_code)
            self.assertIsNone(response.data)
