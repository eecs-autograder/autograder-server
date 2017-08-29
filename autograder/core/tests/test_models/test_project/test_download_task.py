from django.core.exceptions import ValidationError

import autograder.core.models as ag_models
from autograder.utils.testing import UnitTestBase
import autograder.utils.testing.model_obj_builders as obj_build


class DownloadTaskTestCase(UnitTestBase):
    def setUp(self):
        super().setUp()
        self.project = obj_build.build_project()
        [self.user] = obj_build.make_users(1)

    def test_valid_create(self):
        task = ag_models.DownloadTask.objects.validate_and_create(
            project=self.project, creator=self.user,
            download_type=ag_models.DownloadType.all_submission_files
        )  # type: ag_models.DownloadTask
        task.refresh_from_db()
        self.assertEqual(self.project, task.project)
        self.assertEqual(self.user, task.creator)
        self.assertEqual(0, task.progress)
        self.assertEqual('', task.error_msg)
        self.assertEqual(ag_models.DownloadType.all_submission_files, task.download_type)
        self.assertEqual('', task.result_filename)
        self.assertFalse(task.has_error)

        self.assertSequenceEqual([task], self.project.download_tasks.all())

    def test_error_progress_out_of_range(self):
        with self.assertRaises(ValidationError) as cm:
            ag_models.DownloadTask.objects.validate_and_create(
                project=self.project, creator=self.user,
                download_type=ag_models.DownloadType.all_submission_files,
                progress=-5)
        self.assertIn('progress', cm.exception.message_dict)

        with self.assertRaises(ValidationError) as cm:
            ag_models.DownloadTask.objects.validate_and_create(
                project=self.project, creator=self.user,
                download_type=ag_models.DownloadType.all_submission_files,
                progress=110)
        self.assertIn('progress', cm.exception.message_dict)

    def test_serialization(self):
        expected_fields = [
            'pk',
            'project',
            'download_type',
            'result_filename',
            'progress',
            'error_msg',
        ]

        task = ag_models.DownloadTask.objects.validate_and_create(
            project=self.project, creator=self.user,
            download_type=ag_models.DownloadType.all_submission_files
        )  # type: ag_models.DownloadTask

        serialized = task.to_dict()
        self.assertCountEqual(expected_fields, serialized.keys())

        self.assertEqual(self.project.pk, serialized['project'])

        task.validate_and_update(result_filename='/a/file', progress=50, error_msg='waaaluigi')
        self.assertTrue(task.has_error)
