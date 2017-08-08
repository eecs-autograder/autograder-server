from django.test import tag

from rest_framework import status
from rest_framework.test import APIClient

import autograder.core.models as ag_models

import autograder.utils.testing as test_ut
import autograder.rest_api.tests.test_views.common_generic_data as test_data


@tag('slow')
class RaceConditionTestCase(test_data.Client,
                            test_data.Project,
                            test_data.Group,
                            test_ut.UnitTestBase):
    def test_simultaneous_create_race_condition_prevented(self):
        group = self.admin_group(self.project)
        group_id = group.pk
        path = 'autograder.rest_api.views.submission_views.submissions_view.user_can_view_group'

        @test_ut.sleeper_subtest(path)
        def create_submission_first(group_id):
            group = ag_models.SubmissionGroup.objects.get(pk=group_id)
            client = APIClient()
            client.force_authenticate(group.members.first())
            response = client.post(self.submissions_url(group),
                                   {'submitted_files': []},
                                   format='multipart')
            self.assertEqual(status.HTTP_201_CREATED, response.status_code)
            self.assertEqual(1, ag_models.Submission.objects.count())

        subtest = create_submission_first(group_id)
        self.client.force_authenticate(self.admin)
        response = self.client.post(self.submissions_url(group),
                                    {'submitted_files': []},
                                    format='multipart')
        subtest.join()
        self.assertEqual(status.HTTP_400_BAD_REQUEST, response.status_code)
        self.assertEqual(1, ag_models.Submission.objects.count())
