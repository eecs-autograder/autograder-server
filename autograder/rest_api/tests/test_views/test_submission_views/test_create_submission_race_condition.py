from django.test import tag
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APIClient

import autograder.core.models as ag_models
import autograder.utils.testing as test_ut
import autograder.utils.testing.model_obj_builders as obj_build
from autograder.rest_api.tests.test_views.ag_view_test_base import AGViewTestBase


@tag('slow')
class RaceConditionTestCase(test_ut.TransactionUnitTestBase):
    client: APIClient

    def setUp(self) -> None:
        super().setUp()
        self.client = APIClient()

    def test_simultaneous_create_race_condition_prevented(self) -> None:
        project = obj_build.make_project()
        group = obj_build.make_group(project=project, members_role=obj_build.UserRole.admin)
        group_id = group.pk
        path = 'autograder.rest_api.views.submission_views.submission_views.test_ut.mocking_hook'

        @test_ut.sleeper_subtest(path)
        def create_submission_first(group_id):
            group = ag_models.Group.objects.get(pk=group_id)
            client = APIClient()
            client.force_authenticate(group.members.first())
            response = client.post(reverse('submissions', kwargs={'pk': group.pk}),
                                   {'submitted_files': []},
                                   format='multipart')
            self.assertEqual(status.HTTP_201_CREATED, response.status_code,
                             msg=response.data)
            self.assertEqual(1, ag_models.Submission.objects.count())

        subtest = create_submission_first(group_id)
        self.client.force_authenticate(group.members.first())
        response = self.client.post(reverse('submissions', kwargs={'pk': group.pk}),
                                    {'submitted_files': []},
                                    format='multipart')
        subtest.join()
        self.assertEqual(status.HTTP_400_BAD_REQUEST, response.status_code)
        self.assertEqual(1, ag_models.Submission.objects.count())
