import random

from django.core.urlresolvers import reverse

from rest_framework import status
from rest_framework.test import APIClient

import autograder.core.models as ag_models
import autograder.rest_api.serializers as ag_serializers

from autograder.core.tests.temporary_filesystem_test_case import (
    TemporaryFilesystemTestCase)
import autograder.core.tests.dummy_object_utils as obj_ut


class _TestDataSingleton:
    def setUp(self):
        self.client = APIClient()

    # def tearDown(self):
    #     self._course = None

    def course(self):
        if not hasattr(self, '_course'):
            self._course = obj_ut.build_course()

        return self._course

    @property
    def admin(self):
        if not hasattr(self, '_admin'):
            self._admin = obj_ut.create_dummy_user()
            self.course.administrators.add(self._admin)

        return self._admin

    @property
    def staff(self):
        if not hasattr(self, '_staff'):
            self._staff = obj_ut.create_dummy_user()
            self.course.staff.add(self._staff)

        return self._staff

    @property
    def enrolled(self):
        if not hasattr(self, '_enrolled'):
            self._enrolled = obj_ut.create_dummy_user()
            self.course.enrolled_students.add(self._enrolled)

        return self._enrolled

    @property
    def nobody(self):
        if not hasattr(self, '_nobody'):
            self._nobody = obj_ut.create_dummy_user()

        return self._nobody


    @property
    def project(self):
        self._project = ag_models.Project.objects.validate_and_create(
            name='spammy' + random.choice('qewiurqelrhjk'),
            course=self.course)

        return self._project


class _PatternSetUp:
    def setUp(self):
        super().setUp()

        self.client = APIClient()

        self.course = obj_ut.build_course()

        self.admin = obj_ut.create_dummy_user()
        self.course.administrators.add(self.admin)

        self.staff = obj_ut.create_dummy_user()
        self.course.staff.add(self.staff)

        self.enrolled = obj_ut.create_dummy_user()
        self.course.enrolled_students.add(self.enrolled)

        self.nobody = obj_ut.create_dummy_user()

        self.project = ag_models.Project.objects.validate_and_create(
            name='spammy', course=self.course)
        self.url = reverse('project-patterns-list', kwargs={'pk': self.project.pk})


class ListPatternsTestCase(_PatternSetUp, TemporaryFilesystemTestCase):
    def setUp(self):
        num_patterns = 4
        for i in range(num_patterns):
            min_matches = random.randint(0, 3)
            max_matches = min_matches + 2
            ag_models.ExpectedStudentFilePattern.objects.validate_and_create(
                project=self.project,
                pattern=random.choice('adsflkjhqweriouyzxcvmnb'),
                min_num_matches=min_matches,
                max_num_matches=max_matches)

        self.serialized_patterns = (
            ag_serializers.ExpectedStudentFilePatternSerializer(
                self.project.expected_student_file_patterns.all(), many=True)
        ).data
        self.assertEqual(num_patterns, len(self.serialized_patterns))

    def test_admin_list_patterns(self):

        self.fail()

    def test_staff_list_patterns(self):
        self.fail()

    def test_enrolled_list_patterns_visible_project(self):
        self.fail()

    def test_enrolled_list_patterns_hidden_project_permission_denied(self):
        self.fail()

    def test_other_list_patterns_visible_public_project(self):
        self.fail()

    def test_other_list_patterns_hidden_public_project_permission_denied(self):
        self.fail()

    def test_other_list_patterns_non_public_project_permission_denied(self):
        self.fail()

    def do_list_patterns_test(self, user):
        self.client.force_authenticate(user)
        response = self.client.get(self.url)
        self.assertEqual(status.HTTP_200_OK, response.status_code)
        self.assertCountEqual(self.serialized_patterns, response.data)

    def do_permission_denied_test(self, user):
        self.client.force_authenticate(user)
        response = self.client.get(self.url)
        self.assertEqual(status.HTTP_403_FORBIDDEN, response.status_code)


class CreatePatternTestCase(_PatternSetUp, TemporaryFilesystemTestCase):
    def test_admin_create_pattern(self):
        self.fail()

    def test_admin_create_pattern_invalid_settings(self):
        self.fail()

    def test_other_create_pattern_permission_denied(self):
        self.fail()
