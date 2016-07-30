from rest_framework import status
from rest_framework.test import APIClient

import autograder.core.models as ag_models

from autograder.core.tests.temporary_filesystem_test_case import (
    TemporaryFilesystemTestCase)
import autograder.rest_api.tests.test_views.common_generic_data as test_data

from .sleeper_subtest import sleeper_subtest


class RaceConditionTestCase(test_data.Client,
                            test_data.Project,
                            test_data.Group,
                            TemporaryFilesystemTestCase):
    def test_simultaneous_create_race_condition_prevented(self):
        group = self.admin_group(self.project)
        group_id = group.pk
        path = ('autograder.rest_api.views.group_views.'
                'group_submissions_view.user_can_view_group')

        @sleeper_subtest(path)
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
        self.assertEqual(status.HTTP_403_FORBIDDEN, response.status_code)
        self.assertEqual(1, ag_models.Submission.objects.count())
