
class AGTestSuiteOutputFeedbackTestCase(_FeedbackTestsBase):

    def test_get_suite_result_setup_output_visible(self):
        self.assertTrue(self.ag_test_suite.normal_fdbk_config.show_setup_stdout)
        self.assertTrue(self.ag_test_suite.normal_fdbk_config.show_setup_stderr)
        self.assertTrue(self.ag_test_suite.normal_fdbk_config.visible)

        self.client.force_authenticate(self.student1)

        suite_res = self.student1_normal_res.ag_test_case_result.ag_test_suite_result
        self._do_suite_result_output_test(self.client, suite_res.submission, suite_res,
                                          ag_models.FeedbackCategory.normal)

    def test_get_suite_result_setup_output_hidden(self):
        self.ag_test_suite.validate_and_update(normal_fdbk_config={'show_setup_stdout': False})
        self.ag_test_suite.validate_and_update(normal_fdbk_config={'show_setup_stderr': False})
        self.assertTrue(self.ag_test_suite.normal_fdbk_config.visible)

        self.client.force_authenticate(self.student1)

        suite_res = self.student1_normal_res.ag_test_case_result.ag_test_suite_result
        self._do_suite_result_output_test(self.client, suite_res.submission, suite_res,
                                          ag_models.FeedbackCategory.normal)

    def test_suite_result_output_requested_on_not_visible_suite(self):
        self.ag_test_suite.validate_and_update(normal_fdbk_config={'visible': False})
        self.assertTrue(self.ag_test_suite.normal_fdbk_config.show_setup_stdout)
        self.assertTrue(self.ag_test_suite.normal_fdbk_config.show_setup_stderr)

        self.client.force_authenticate(self.student1)

        suite_res = self.student1_normal_res.ag_test_case_result.ag_test_suite_result
        self._do_suite_result_output_test(self.client, suite_res.submission, suite_res,
                                          ag_models.FeedbackCategory.normal)

    def test_suite_result_output_requested_suite_doesnt_exist_404(self):
        self.client.force_authenticate(self.staff)

        suite_result = self.staff_normal_res.ag_test_case_result.ag_test_suite_result

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

        for field_name, url_lookup in zip(field_names, url_lookups):
            url_kwargs = {
                'pk': self.staff_normal_submission.pk,
                'result_pk': suite_result_pk}
            url = (reverse(url_lookup, kwargs=url_kwargs)
                   + f'?feedback_category={ag_models.FeedbackCategory.max.value}')
            response = self.client.get(url)
            self.assertEqual(status.HTTP_404_NOT_FOUND, response.status_code)

    def _do_suite_result_output_test(self, client, submission, suite_result, fdbk_category,
                                     expect_404=False):
        with suite_result.open_setup_stdout('w') as f:
            f.write('adkjfaksdjf;akjsdf;')
        with suite_result.open_setup_stderr('w') as f:
            f.write('qewiruqpewpuir')

        field_names = ['setup_stdout', 'setup_stderr']
        url_lookups = [
            'ag-test-suite-result-stdout',
            'ag-test-suite-result-stderr'
        ]
        for field_name, url_lookup in zip(field_names, url_lookups):
            print(url_lookup)
            url = (reverse(url_lookup,
                           kwargs={'pk': submission.pk, 'result_pk': suite_result.pk})
                   + '?feedback_category={}'.format(fdbk_category.value))
            response = client.get(url)
            if expect_404:
                self.assertEqual(status.HTTP_404_NOT_FOUND, response.status_code)
                continue

            fdbk = get_suite_fdbk(suite_result, fdbk_category)
            expected = getattr(fdbk, field_name)
            if expected is None or not fdbk.fdbk_conf.visible:
                self.assertIsNone(response.data)
            else:
                self.assertEqual(expected.read(),
                                 b''.join((chunk for chunk in response.streaming_content)))


class AGTestCommandOutputFeedbackTestCase(_FeedbackTestsBase):
    def setUp(self):
        super().setUp()

    # FIXME

    def test_cmd_result_output_or_diff_requested_on_cmd_in_not_visible_suite(self):
        self.ag_test_suite.validate_and_update(normal_fdbk_config={'visible': False})
        self.client.force_authenticate(self.student1)
        self.do_get_output_and_diff_on_hidden_ag_test_test(
            self.client, self.student_group1_normal_submission,
            self.student1_normal_res, ag_models.FeedbackCategory.normal)

    def test_cmd_result_output_or_diff_requested_on_cmd_in_not_visible_case(self):
        self.ag_test_case.validate_and_update(normal_fdbk_config={'visible': False})
        self.client.force_authenticate(self.student1)
        self.do_get_output_and_diff_on_hidden_ag_test_test(
            self.client, self.student_group1_normal_submission,
            self.student1_normal_res, ag_models.FeedbackCategory.normal)

    def test_cmd_result_output_or_diff_requested_on_not_visible_cmd(self):
        self.ag_test_cmd.validate_and_update(normal_fdbk_config={'visible': False})
        self.client.force_authenticate(self.student1)
        self.do_get_output_and_diff_on_hidden_ag_test_test(
            self.client, self.student_group1_normal_submission,
            self.student1_normal_res, ag_models.FeedbackCategory.normal)

    def test_cmd_result_output_or_diff_requested_individual_cmds_not_shown(self):
        self.ag_test_case.validate_and_update(
            normal_fdbk_config={'show_individual_commands': False})
        self.client.force_authenticate(self.student1)
        self.do_get_output_and_diff_on_hidden_ag_test_test(
            self.client, self.student_group1_normal_submission,
            self.student1_normal_res, ag_models.FeedbackCategory.normal)

    def test_cmd_result_output_or_diff_requested_individual_cases_not_shown(self):
        self.ag_test_suite.validate_and_update(normal_fdbk_config={'show_individual_tests': False})
        self.client.force_authenticate(self.student1)
        self.do_get_output_and_diff_on_hidden_ag_test_test(
            self.client, self.student_group1_normal_submission,
            self.student1_normal_res, ag_models.FeedbackCategory.normal)

    def test_cmd_diff_with_non_utf_chars(self):
        non_utf_bytes = b'\x80 and some other stuff just because\n'
        output = 'some stuff'
        self.ag_test_cmd.validate_and_update(
            expected_stdout_source=ag_models.ExpectedOutputSource.text,
            expected_stdout_text=output,
            expected_stderr_source=ag_models.ExpectedOutputSource.text,
            expected_stderr_text=output,
        )
        with open(self.staff_normal_res.stdout_filename, 'wb') as f:
            f.write(non_utf_bytes)
        with open(self.staff_normal_res.stderr_filename, 'wb') as f:
            f.write(non_utf_bytes)
        self.client.force_authenticate(self.staff)
        url = (reverse('ag-test-cmd-result-stdout-diff',
                       kwargs={'pk': self.staff_normal_submission.pk,
                               'result_pk': self.staff_normal_res.pk})
               + '?feedback_category=max')

        expected_diff = ['- ' + output, '+ ' + non_utf_bytes.decode('utf-8', 'surrogateescape')]
        response = self.client.get(url)
        self.assertEqual(status.HTTP_200_OK, response.status_code)
        self.assertEqual(expected_diff, json.loads(response.content.decode('utf-8')))

        url = (reverse('ag-test-cmd-result-stderr-diff',
                       kwargs={'pk': self.staff_normal_submission.pk,
                               'result_pk': self.staff_normal_res.pk})
               + '?feedback_category=max')
        response = self.client.get(url)
        self.assertEqual(status.HTTP_200_OK, response.status_code)
        self.assertEqual(expected_diff, json.loads(response.content.decode('utf-8')))

    def test_cmd_result_output_or_diff_requested_cmd_doesnt_exist_404(self):
        urls_and_field_names = self.get_output_and_diff_test_urls(
            self.staff_normal_submission,
            self.staff_normal_res,
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
        urls_and_field_names = self.get_output_and_diff_test_urls(
            submission, cmd_result, fdbk_category)
        for url, field_name in urls_and_field_names:
            response = client.get(url)
            self.assertEqual(status.HTTP_200_OK, response.status_code)
            self.assertIsNone(response.data)

