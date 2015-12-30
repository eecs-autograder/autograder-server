import itertools

from django.core.urlresolvers import reverse
from django.core.files.uploadedfile import SimpleUploadedFile

from autograder.core.models import (
    AutograderTestCaseFactory, SubmissionGroup, Submission, Project,
    AutograderTestCaseResult, StudentTestSuiteFactory, StudentTestSuiteResult)

from autograder.core.tests.temporary_filesystem_test_case import (
    TemporaryFilesystemTestCase)
import autograder.core.tests.dummy_object_utils as obj_ut
from .utilities import MockClient, json_load_bytes, sorted_by_pk

import autograder.core.shared.feedback_configuration as fbc


def _get_submission_url(submission):
    return reverse('submission:get', kwargs={'pk': submission.pk})


def _get_ag_test_result_url(result):
    return reverse('test-result:get', kwargs={'pk': result.pk})


class GetAutograderTestCaseResultTestCase(TemporaryFilesystemTestCase):
    def setUp(self):
        super().setUp()

        self.admin = obj_ut.create_dummy_user()
        self.staff = obj_ut.create_dummy_user()
        self.enrolled = obj_ut.create_dummy_user()
        self.nobody = obj_ut.create_dummy_user()

        self.files_to_submit = [
            SimpleUploadedFile('file1.cpp', b'blah'),
            SimpleUploadedFile('file2.cpp', b'blee'),
            SimpleUploadedFile('file3.cpp', b'bloo'),
        ]

        self.filenames_to_submit = [
            file_.name for file_ in self.files_to_submit]

        self.project = obj_ut.build_project(
            course_kwargs={'administrators': [self.admin]},
            semester_kwargs={
                'staff': [self.staff], 'enrolled_students': [self.enrolled]},
            project_kwargs={
                'allow_submissions_from_non_enrolled_students': True,
                'visible_to_students': True,
                'required_student_files': self.filenames_to_submit})

        self.semester = self.project.semester
        self.course = self.semester.course

        self.points_for_test = 2

        self.test_case = AutograderTestCaseFactory.validate_and_create(
            'compiled_and_run_test_case',
            name='testy', project=self.project,
            expected_return_code=0,
            points_for_correct_return_code=self.points_for_test,
            compiler='g++',
            files_to_compile_together=self.filenames_to_submit,
            student_resource_files=self.filenames_to_submit,
            executable_name='prog')

        self.admin_submission_obj = self._make_submission_obj(
            self.admin, self.project)
        self.staff_submission_obj = self._make_submission_obj(
            self.staff, self.project)
        self.enrolled_submission_obj = self._make_submission_obj(
            self.enrolled, self.project)
        self.nobody_submission_obj = self._make_submission_obj(
            self.nobody, self.project)

        self.submission_objs = [
            self.admin_submission_obj, self.staff_submission_obj,
            self.enrolled_submission_obj, self.nobody_submission_obj
        ]

        for obj in self.submission_objs:
            obj['result'] = AutograderTestCaseResult.objects.create(
                test_case=self.test_case,
                submission=obj['submission'],
                compilation_return_code=0,
                return_code=0)

            obj['result_url'] = _get_ag_test_result_url(obj['result'])

    def _make_submission_obj(self, user, project):
        obj = {
            'user': user,
            'group': SubmissionGroup.objects.validate_and_create(
                members=[user.username], project=project),
        }
        obj['group_url'] = reverse('group:get', kwargs={'pk': obj['group'].pk})

        obj['submission'] = Submission.objects.validate_and_create(
            submitted_files=self.files_to_submit,
            submission_group=obj['group']
        )
        obj['submission_url'] = _get_submission_url(obj['submission'])

        return obj

    def test_student_get_own_visible_result(self):
        for obj in self.enrolled_submission_obj, self.nobody_submission_obj:
            client = MockClient(obj['user'])
            response = client.get(obj['result_url'])
            self.assertEqual(200, response.status_code)

            expected_content = {
                'type': 'autograder_test_case_result',
                'id': obj['result'].pk,
                'urls': {
                    "self": obj['result_url'],
                    "submission": obj['submission_url']
                }
            }
            expected_content.update(obj['result'].to_json())

            self.assertEqual(
                expected_content, json_load_bytes(response.content))

    def test_course_admin_or_semester_staff_get_other_user_visible_result(self):
        # should get max feedback on result
        for user in self.admin, self.staff:
            client = MockClient(user)
            for obj in self.submission_objs:
                response = client.get(obj['result_url'])
                self.assertEqual(200, response.status_code)

                expected_content = {
                    'type': 'autograder_test_case_result',
                    'id': obj['result'].pk,
                    'urls': {
                        "self": obj['result_url'],
                        "submission": obj['submission_url']
                    }
                }
                expected_content.update(obj['result'].to_json(
                    (fbc.AutograderTestCaseFeedbackConfiguration.
                        get_max_feedback())))

                self.assertEqual(
                    expected_content, json_load_bytes(response.content))

    def test_course_admin_or_semester_staff_get_other_user_hidden_result_permission_denied(self):
        self.test_case.feedback_configuration.visibility_level = (
            fbc.VisibilityLevel.hide_from_students)
        self.test_case.validate_and_save()

        for user in self.admin, self.staff:
            client = MockClient(user)
            for obj in self.submission_objs:
                response = client.get(obj['result_url'])
                self.assertEqual(403, response.status_code)

    def test_student_get_own_hidden_result_permission_denied(self):
        self.test_case.feedback_configuration.visibility_level = (
            fbc.VisibilityLevel.hide_from_students)
        self.test_case.validate_and_save()

        for obj in self.enrolled_submission_obj, self.nobody_submission_obj:
            client = MockClient(obj['user'])
            response = client.get(obj['result_url'])
            self.assertEqual(403, response.status_code)

    def test_student_get_other_student_result_permission_denied(self):
        for user in self.enrolled, self.nobody:
            client = MockClient(user)
            for obj in self.submission_objs:
                response = client.get(obj['result_url'])
                self.assertEqual(403, response.status_code)

    def test_student_get_own_visible_result_project_hidden_permission_denied(self):
        self.project.visible_to_students = False
        self.project.validate_and_save()

        for obj in self.enrolled_submission_obj, self.nobody_submission_obj:
            client = MockClient(obj['user'])
            response = client.get(obj['result_url'])
            self.assertEqual(403, response.status_code)

    def test_non_enrolled_student_non_public_project_get_own_visible_result_permission_denied(self):
        self.project.allow_submissions_from_non_enrolled_students = False
        self.project.validate_and_save()

        client = MockClient(self.nobody_submission_obj['user'])
        response = client.get(self.nobody_submission_obj['result_url'])
        self.assertEqual(403, response.status_code)
