from pathlib import Path

from django.conf import settings
from django.http import QueryDict
from django.test.utils import override_settings
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APIClient

import autograder.core.models as ag_models
import autograder.utils.testing.model_obj_builders as obj_build
from autograder.core.submission_feedback import MutationTestSuitePreLoader
from autograder.utils.testing import UnitTestBase


class MutationTestSuiteResultsTestCase(UnitTestBase):
    def setUp(self):
        super().setUp()
        self.project = obj_build.make_project()
        self.mutation_suite = ag_models.MutationTestSuite.objects.validate_and_create(
            name='suitte', project=self.project,
            buggy_impl_names=['bug{}'.format(i) for i in range(4)],
            setup_command={
                'cmd': 'echo "hello world"'
            },
            points_per_exposed_bug=2,
            normal_fdbk_config={
                'bugs_exposed_fdbk_level': ag_models.BugsExposedFeedbackLevel.num_bugs_exposed,
                'show_invalid_test_names': True,
            }
        )  # type: ag_models.MutationTestSuite

        self.submission = obj_build.make_submission(
            group=obj_build.make_group(
                project=self.project, members_role=obj_build.UserRole.admin))

        self.setup_stdout = 'setupp stdouttt'
        self.setup_stderr = 'sortoop stdear'
        self.get_test_names_stdout = 'test narmes stdout'
        self.get_test_names_stderr = 'test nurmes stderr'
        self.validity_check_stdout = 'valooditee chorck stdout'
        self.validity_check_stderr = 'valaerditi charck stderr'
        self.buggy_impls_stdout = 'borgy oomples stdout'
        self.buggy_impls_stderr = 'baergy eyemples stderr'

        setup_result = ag_models.AGCommandResult.objects.validate_and_create(
            return_code=0
        )  # type: ag_models.AGCommandResult
        with open(setup_result.stdout_filename, 'w') as f:
            f.write(self.setup_stdout)
        with open(setup_result.stderr_filename, 'w') as f:
            f.write(self.setup_stderr)

        get_test_names_result = ag_models.AGCommandResult.objects.validate_and_create(
            return_code=0
        )  # type: ag_models.AGCommandResult
        with open(get_test_names_result.stdout_filename, 'w') as f:
            f.write(self.get_test_names_stdout)
        with open(get_test_names_result.stderr_filename, 'w') as f:
            f.write(self.get_test_names_stderr)

        student_tests = ['test{}'.format(i) for i in range(5)]
        self.mutation_suite_result = ag_models.MutationTestSuiteResult.objects.validate_and_create(
            mutation_test_suite=self.mutation_suite,
            submission=self.submission,
            student_tests=student_tests,
            invalid_tests=student_tests[:-1],
            timed_out_tests=student_tests[:1],
            bugs_exposed=self.mutation_suite.buggy_impl_names[:-1],
            setup_result=setup_result,
            get_test_names_result=get_test_names_result
        )  # type: ag_models.MutationTestSuiteResult

        with open(self.mutation_suite_result.validity_check_stdout_filename, 'w') as f:
            f.write(self.validity_check_stdout)
        with open(self.mutation_suite_result.validity_check_stderr_filename, 'w') as f:
            f.write(self.validity_check_stderr)
        with open(self.mutation_suite_result.grade_buggy_impls_stdout_filename, 'w') as f:
            f.write(self.buggy_impls_stdout)
        with open(self.mutation_suite_result.grade_buggy_impls_stderr_filename, 'w') as f:
            f.write(self.buggy_impls_stderr)

        self.client = APIClient()
        self.admin = self.submission.group.members.first()

        self.setup_stdout_base_url = reverse(
            'mutation-suite-setup-stdout',
            kwargs={'pk': self.submission.pk, 'result_pk': self.mutation_suite_result.pk})
        self.setup_stderr_base_url = reverse(
            'mutation-suite-setup-stderr',
            kwargs={'pk': self.submission.pk, 'result_pk': self.mutation_suite_result.pk})
        self.get_test_names_stdout_base_url = reverse(
            'mutation-suite-get-student-test-names-stdout',
            kwargs={'pk': self.submission.pk, 'result_pk': self.mutation_suite_result.pk})
        self.get_test_names_stderr_base_url = reverse(
            'mutation-suite-get-student-test-names-stderr',
            kwargs={'pk': self.submission.pk, 'result_pk': self.mutation_suite_result.pk})
        self.validity_check_stdout_base_url = reverse(
            'mutation-suite-validity-check-stdout',
            kwargs={'pk': self.submission.pk, 'result_pk': self.mutation_suite_result.pk})
        self.validity_check_stderr_base_url = reverse(
            'mutation-suite-validity-check-stderr',
            kwargs={'pk': self.submission.pk, 'result_pk': self.mutation_suite_result.pk})
        self.buggy_impls_stdout_base_url = reverse(
            'mutation-suite-grade-buggy-impls-stdout',
            kwargs={'pk': self.submission.pk, 'result_pk': self.mutation_suite_result.pk})
        self.buggy_impls_stderr_base_url = reverse(
            'mutation-suite-grade-buggy-impls-stderr',
            kwargs={'pk': self.submission.pk, 'result_pk': self.mutation_suite_result.pk})

        self.base_urls = [
            self.setup_stdout_base_url,
            self.setup_stderr_base_url,
            self.get_test_names_stdout_base_url,
            self.get_test_names_stderr_base_url,
            self.validity_check_stdout_base_url,
            self.validity_check_stderr_base_url,
            self.buggy_impls_stdout_base_url,
            self.buggy_impls_stderr_base_url,
        ]

        self.submission.refresh_from_db()

    def test_suite_results_included_in_submission_detail_response(self):
        self.client.force_authenticate(self.admin)

        self.maxDiff = None
        self.assertNotEqual(0, self.submission.mutation_test_suite_results.count())

        query_params = QueryDict(mutable=True)
        query_params.update({'feedback_category': ag_models.FeedbackCategory.max.value})
        url = (reverse('submission-results', kwargs={'pk': self.submission.pk})
               + '?' + query_params.urlencode())

        response = self.client.get(url)
        expected_content = [
            self.mutation_suite_result.get_fdbk(
                ag_models.FeedbackCategory.max,
                MutationTestSuitePreLoader(self.project)
            ).to_dict()
        ]
        self.assertEqual(status.HTTP_200_OK, response.status_code)
        self.assertSequenceEqual(expected_content, response.data['mutation_test_suite_results'])

    def test_get_setup_output(self):
        self.do_get_output_test(
            self.client, self.admin, ag_models.FeedbackCategory.max,
            status.HTTP_200_OK, self.setup_stdout, self.setup_stdout_base_url)

        self.do_get_output_test(
            self.client, self.admin, ag_models.FeedbackCategory.normal,
            status.HTTP_200_OK, None, self.setup_stdout_base_url)

        self.do_get_output_test(
            self.client, self.admin, ag_models.FeedbackCategory.max,
            status.HTTP_200_OK, self.setup_stderr, self.setup_stderr_base_url)

        self.do_get_output_test(
            self.client, self.admin, ag_models.FeedbackCategory.normal,
            status.HTTP_200_OK, None, self.setup_stderr_base_url)

    def test_get_setup_output_no_setup_cmd(self):
        self.mutation_suite.validate_and_update(use_setup_command=False)
        self.mutation_suite_result.setup_result = None
        self.mutation_suite_result.save()

        self.do_get_output_test(
            self.client, self.admin, ag_models.FeedbackCategory.max,
            status.HTTP_200_OK, None, self.setup_stdout_base_url)

        self.do_get_output_test(
            self.client, self.admin, ag_models.FeedbackCategory.max,
            status.HTTP_200_OK, None, self.setup_stderr_base_url)

    def test_get_get_test_names_result_output(self):
        self.do_get_output_test(
            self.client, self.admin, ag_models.FeedbackCategory.max,
            status.HTTP_200_OK, self.get_test_names_stdout, self.get_test_names_stdout_base_url)

        self.do_get_output_test(
            self.client, self.admin, ag_models.FeedbackCategory.normal,
            status.HTTP_200_OK, None, self.get_test_names_stdout_base_url)

        self.do_get_output_test(
            self.client, self.admin, ag_models.FeedbackCategory.max,
            status.HTTP_200_OK, self.get_test_names_stderr, self.get_test_names_stderr_base_url)

        self.do_get_output_test(
            self.client, self.admin, ag_models.FeedbackCategory.normal,
            status.HTTP_200_OK, None, self.get_test_names_stderr_base_url)

    def test_get_validity_check_output(self):
        self.do_get_output_test(
            self.client, self.admin, ag_models.FeedbackCategory.max,
            status.HTTP_200_OK, self.validity_check_stdout, self.validity_check_stdout_base_url)

        self.do_get_output_test(
            self.client, self.admin, ag_models.FeedbackCategory.normal,
            status.HTTP_200_OK, None, self.validity_check_stdout_base_url)

        self.do_get_output_test(
            self.client, self.admin, ag_models.FeedbackCategory.max,
            status.HTTP_200_OK, self.validity_check_stderr, self.validity_check_stderr_base_url)

        self.do_get_output_test(
            self.client, self.admin, ag_models.FeedbackCategory.normal,
            status.HTTP_200_OK, None, self.validity_check_stderr_base_url)

    def test_get_buggy_impls_output(self):
        self.do_get_output_test(
            self.client, self.admin, ag_models.FeedbackCategory.max,
            status.HTTP_200_OK, self.buggy_impls_stdout, self.buggy_impls_stdout_base_url)

        self.do_get_output_test(
            self.client, self.admin, ag_models.FeedbackCategory.normal,
            status.HTTP_200_OK, None, self.buggy_impls_stdout_base_url)

        self.do_get_output_test(
            self.client, self.admin, ag_models.FeedbackCategory.max,
            status.HTTP_200_OK, self.buggy_impls_stderr, self.buggy_impls_stderr_base_url)

        self.do_get_output_test(
            self.client, self.admin, ag_models.FeedbackCategory.normal,
            status.HTTP_200_OK, None, self.buggy_impls_stderr_base_url)

    def test_get_output_suite_hidden(self):
        self.maxDiff = None
        expected_fdbk_settings = self.mutation_suite_result.get_fdbk(
            ag_models.FeedbackCategory.max,
            MutationTestSuitePreLoader(self.project)
        ).fdbk_settings
        expected_fdbk_settings['bugs_exposed_fdbk_level'] = (
            ag_models.BugsExposedFeedbackLevel.exposed_bug_names.value)

        staff_viewer_fdbk_settings = self.mutation_suite_result.get_fdbk(
            ag_models.FeedbackCategory.staff_viewer,
            MutationTestSuitePreLoader(self.project)
        ).fdbk_settings
        self.assertEqual(expected_fdbk_settings, staff_viewer_fdbk_settings)

        self.mutation_suite.validate_and_update(staff_viewer_fdbk_config={
            'visible': False
        })

        for url in self.base_urls:
            self.do_get_output_test(
                self.client, self.admin, ag_models.FeedbackCategory.staff_viewer,
                status.HTTP_200_OK, None, url)

        url = self.make_output_size_url(ag_models.FeedbackCategory.staff_viewer)
        response = self.client.get(url)
        self.assertEqual(status.HTTP_200_OK, response.status_code)
        self.assertIsNone(response.data)

    def test_get_output_suite_not_found(self):
        url_lookups = [
            'mutation-suite-setup-stdout',
            'mutation-suite-setup-stderr',
            'mutation-suite-get-student-test-names-stdout',
            'mutation-suite-get-student-test-names-stderr',
            'mutation-suite-validity-check-stdout',
            'mutation-suite-validity-check-stderr',
            'mutation-suite-grade-buggy-impls-stdout',
            'mutation-suite-grade-buggy-impls-stderr',
            'mutation-suite-result-output-size'
        ]

        for url_lookup in url_lookups:
            url_with_bad_pk = reverse(url_lookup, kwargs={'pk': 9001, 'result_pk': 9002})
            self.do_get_output_test(
                self.client, self.admin, ag_models.FeedbackCategory.max,
                status.HTTP_404_NOT_FOUND, None, url_with_bad_pk)

    def test_get_output_size(self):
        self.client.force_authenticate(self.admin)

        url = self.make_output_size_url(ag_models.FeedbackCategory.max)
        response = self.client.get(url)

        self.assertEqual(status.HTTP_200_OK, response.status_code)
        expected = {
            'setup_stdout_size': len(self.setup_stdout),
            'setup_stderr_size': len(self.setup_stderr),
            'get_student_test_names_stdout_size': len(self.get_test_names_stdout),
            'get_student_test_names_stderr_size': len(self.get_test_names_stderr),
            'validity_check_stdout_size': len(self.validity_check_stdout),
            'validity_check_stderr_size': len(self.validity_check_stderr),
            'grade_buggy_impls_stdout_size': len(self.buggy_impls_stdout),
            'grade_buggy_impls_stderr_size': len(self.buggy_impls_stderr),
        }
        self.assertEqual(expected, response.data)

    def test_get_output_x_accel(self) -> None:
        self.client.force_authenticate(self.admin)

        self.do_get_output_x_accel_test(
            self.setup_stdout_base_url,
            self.mutation_suite_result.setup_result.stdout_filename
        )
        self.do_get_output_x_accel_test(
            self.setup_stderr_base_url,
            self.mutation_suite_result.setup_result.stderr_filename
        )
        self.do_get_output_x_accel_test(
            self.get_test_names_stdout_base_url,
            self.mutation_suite_result.get_test_names_result.stdout_filename
        )
        self.do_get_output_x_accel_test(
            self.get_test_names_stderr_base_url,
            self.mutation_suite_result.get_test_names_result.stderr_filename
        )
        self.do_get_output_x_accel_test(
            self.validity_check_stdout_base_url,
            self.mutation_suite_result.validity_check_stdout_filename
        )
        self.do_get_output_x_accel_test(
            self.validity_check_stderr_base_url,
            self.mutation_suite_result.validity_check_stderr_filename
        )
        self.do_get_output_x_accel_test(
            self.buggy_impls_stdout_base_url,
            self.mutation_suite_result.grade_buggy_impls_stdout_filename
        )
        self.do_get_output_x_accel_test(
            self.buggy_impls_stderr_base_url,
            self.mutation_suite_result.grade_buggy_impls_stderr_filename
        )

    def do_get_output_x_accel_test(self, base_url: str, output_file_path: str):
        with override_settings(USE_NGINX_X_ACCEL=True):
            url = f'{base_url}?feedback_category={ag_models.FeedbackCategory.max.value}'

            response = self.client.get(url)
            self.assertEqual(status.HTTP_200_OK, response.status_code)
            self.assertEqual(b'', response.content)
            self.assertEqual('application/octet-stream', response['Content-Type'])
            self.assertEqual(
                'attachment; filename=' + Path(output_file_path).name,
                response['Content-Disposition']
            )
            self.assertEqual(
                f'/protected{output_file_path[len(settings.MEDIA_ROOT):]}',
                response['X-Accel-Redirect']
            )

    def do_get_output_test(self, client: APIClient, user, fdbk_category,
                           expected_status, expected_output, base_url):
        client.force_authenticate(user)
        query_params = QueryDict(mutable=True)
        query_params.update({'feedback_category': fdbk_category.value})

        url = base_url + '?' + query_params.urlencode()
        response = client.get(url)

        self.assertEqual(expected_status, response.status_code)
        if response.status_code != status.HTTP_200_OK:
            return

        if expected_output is None:
            self.assertIsNone(response.data)
        else:
            self.assertEqual(expected_output,
                             ''.join((chunk.decode() for chunk in response.streaming_content)))

    def make_output_size_url(self, fdbk_category: ag_models.FeedbackCategory):
        url = reverse('mutation-suite-result-output-size',
                      kwargs={'pk': self.submission.pk,
                              'result_pk': self.mutation_suite_result.pk})
        url += f'?feedback_category={fdbk_category.value}'
        return url
