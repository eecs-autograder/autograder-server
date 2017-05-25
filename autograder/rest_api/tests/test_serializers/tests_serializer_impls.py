from django.core.files.uploadedfile import SimpleUploadedFile
from django.http import QueryDict

from rest_framework import request
from rest_framework.test import APIRequestFactory

import autograder.rest_api.serializers as ag_serializers
import autograder.core.models as ag_models
from autograder.utils.testing import UnitTestBase
import autograder.utils.testing.model_obj_builders as obj_build
import autograder.rest_api.tests.test_views.common_generic_data as gen_data

from .serializer_test_case import SerializerTestCase


class CourseSerializerTestCase(SerializerTestCase):
    def setUp(self):
        super().setUp()

    def test_serialize(self):
        course = obj_build.build_course()
        self.do_basic_serialize_test(course, ag_serializers.CourseSerializer)


class ProjectSerializerTestCase(SerializerTestCase):
    def test_serialize(self):
        project = obj_build.build_project()
        data = self.do_basic_serialize_test(project,
                                            ag_serializers.ProjectSerializer)
        self.assertIn('closing_time', data)


class ClosingTimeShownTestCase(gen_data.Project,
                               UnitTestBase):
    def test_admin_shown_closing_time(self):
        get_request = request.Request(APIRequestFactory().get('path'))
        get_request.user = self.admin
        serializer = ag_serializers.ProjectSerializer(
            self.visible_public_project, context={'request': get_request})

        self.assertIn('closing_time', serializer.data)

    def test_non_admin_not_shown_closing_time(self):
        for user in self.staff, self.enrolled, self.nobody:
            get_request = request.Request(APIRequestFactory().get('path'))
            get_request.user = user
            serializer = ag_serializers.ProjectSerializer(
                self.visible_public_project, context={'request': get_request})

            self.assertNotIn('closing_time', serializer.data)

    def test_serialize_many_closing_time_not_included(self):
        for user in self.admin, self.staff, self.enrolled, self.nobody:
            get_request = request.Request(APIRequestFactory().get('path'))
            get_request.user = user
            serializer = ag_serializers.ProjectSerializer(
                self.all_projects, many=True, context={'request': get_request})

            for item in serializer.data:
                self.assertNotIn('closing_time', item)


class ExpectedStudentFilePatternSerializerTestCase(SerializerTestCase):
    def test_serialize(self):
        project = obj_build.build_project()
        pattern = (
            ag_models.ExpectedStudentFilePattern.objects.validate_and_create(
                pattern='spam',
                project=project))
        self.do_basic_serialize_test(
            pattern, ag_serializers.ExpectedStudentFilePatternSerializer)


class UploadedFileSerializerTestCase(SerializerTestCase):
    def test_serialize(self):
        project = obj_build.build_project()
        uploaded_file = ag_models.UploadedFile.objects.validate_and_create(
            file_obj=SimpleUploadedFile('spam', b'waaaaluigi'),
            project=project
        )
        self.do_basic_serialize_test(uploaded_file,
                                     ag_serializers.UploadedFileSerializer)


class SubmissionGroupInvitationSerializerTestCase(SerializerTestCase):
    def test_serialize(self):
        project = obj_build.build_project(
            project_kwargs={
                'max_group_size': 5,
                'allow_submissions_from_non_enrolled_students': True})
        invitation = ag_models.SubmissionGroupInvitation.objects.validate_and_create(
            obj_build.create_dummy_user(),
            obj_build.create_dummy_users(2),
            project=project)
        self.do_basic_serialize_test(
            invitation,
            ag_serializers.SubmissionGroupInvitationSerializer)


class SubmissionGroupSerializerTestCase(SerializerTestCase):
    def test_serialize(self):
        group = obj_build.build_submission_group()
        self.do_basic_serialize_test(group,
                                     ag_serializers.SubmissionGroupSerializer)


class SubmissionSerializerTestCase(SerializerTestCase):
    def test_serialize(self):
        group = obj_build.build_submission_group()
        submission = ag_models.Submission.objects.validate_and_create(
            submitted_files=[],
            submission_group=group)
        self.do_basic_serialize_test(submission,
                                     ag_serializers.SubmissionSerializer)

    def test_create(self):
        files = [SimpleUploadedFile('spam', b'spammo'),
                 SimpleUploadedFile('egg', b'waaaaluigi')]
        data = QueryDict(mutable=True)
        data['submission_group'] = obj_build.build_submission_group()
        # We are adding the files one at a time because of the way that
        # QueryDict appends values to lists
        for file_ in files:
            data.update({'submitted_files': file_})
        # Sanity check for data contents
        self.assertCountEqual(files, data.getlist('submitted_files'))
        self.assertEqual(QueryDict, type(data))

        serializer = ag_serializers.SubmissionSerializer(data=data)
        serializer.is_valid()
        serializer.save()

        self.assertEqual(1, ag_models.Submission.objects.count())
        loaded = ag_models.Submission.objects.first()

        self.assertCountEqual(
            (file_.name for file_ in files), loaded.discarded_files)

    def test_update(self):
        group = obj_build.build_submission_group()
        submission = ag_models.Submission.objects.validate_and_create(
            [], submission_group=group)
        self.assertTrue(submission.count_towards_daily_limit)

        serializer = ag_serializers.SubmissionSerializer(
            submission, data={'count_towards_daily_limit': False})
        serializer.is_valid()
        serializer.save()

        submission.refresh_from_db()

        self.assertFalse(submission.count_towards_daily_limit)


class AGTestSuiteSerializerTestCase(SerializerTestCase):
    def setUp(self):
        super().setUp()

    def test_serialize(self):
        ag_test_suite = obj_build.make_ag_test_suite()
        self.do_basic_serialize_test(ag_test_suite, ag_serializers.AGTestSuiteSerializer)


class NotificationSerializerTestCase(SerializerTestCase):
    def test_serialize(self):
        notification = ag_models.Notification.objects.validate_and_create(
            message='spamspamspam',
            recipient=obj_build.create_dummy_user())
        self.do_basic_serialize_test(notification,
                                     ag_serializers.NotificationSerializer)
