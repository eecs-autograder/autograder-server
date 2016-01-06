import itertools
import datetime
import copy

from django.core.urlresolvers import reverse
from django.utils import timezone, dateparse
from django.core.exceptions import ObjectDoesNotExist
from django.core.files.uploadedfile import SimpleUploadedFile

from autograder.core.models import (
    AutograderTestCaseFactory, SubmissionGroup, Submission, Project,
    AutograderTestCaseResult, StudentTestSuiteFactory, StudentTestSuiteResult)
from autograder.core.tests.temporary_filesystem_test_case import (
    TemporaryFilesystemTestCase)
import autograder.core.tests.dummy_object_utils as obj_ut
from .utilities import MockClient, json_load_bytes, sorted_by_pk

import autograder.core.shared.feedback_configuration as fbc


class _SharedSetUp:
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
                'required_student_files': self.filenames_to_submit,
                'closing_time': timezone.now() + datetime.timedelta(hours=-1)})

        self.semester = self.project.semester
        self.course = self.semester.course

        self.course_url = reverse(
            'course:get', kwargs={'pk': self.course.pk})
        self.semester_url = reverse(
            'semester:get', kwargs={'pk': self.semester.pk})
        self.staff_url = reverse(
            'semester:staff', kwargs={'pk': self.semester.pk})
        self.enrolled_url = reverse(
            'semester:enrolled_students', kwargs={'pk': self.semester.pk})
        self.projects_url = reverse(
            'semester:projects', kwargs={'pk': self.semester.pk})

        self.project_url = reverse(
            'project:get', kwargs={'pk': self.project.pk})

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
        obj['files_url'] = _get_files_url(obj['submission'])

        return obj


def _get_submission_url(submission):
    return reverse('submission:get', kwargs={'pk': submission.pk})


def _get_files_url(submission):
    return reverse('submission:files', kwargs={'pk': submission.pk})


def _get_file_url(submission, filename):
    return reverse(
        'submission:file',
        kwargs={'pk': submission.pk, 'filename': filename})


def _get_ag_test_results_url(submission):
    return reverse('submission:test-results', kwargs={'pk': submission.pk})


def _get_suite_results_url(submission):
    return reverse('submission:suite-results', kwargs={'pk': submission.pk})


def _get_ag_test_result_url(result):
    return reverse('test-result:get', kwargs={'pk': result.pk})


def _get_suite_result_url(result):
    return reverse('suite-result:get', kwargs={'pk': result.pk})


class GetSubmissionTestCase(_SharedSetUp, TemporaryFilesystemTestCase):
    def setUp(self):
        super().setUp()

        self.maxDiff = None

    def test_valid_user_get_own_submission(self):
        for obj in self.submission_objs:
            client = MockClient(obj['user'])
            submission = Submission.objects.validate_and_create(
                submitted_files=self.files_to_submit,
                submission_group=obj['group']
            )

            submission_url = _get_submission_url(submission)
            response = client.get(submission_url)
            self.assertEqual(200, response.status_code)

            expected_content = {
                "type": "submission",
                "id": submission.pk,
                "discarded_files": [],
                "timestamp": submission.timestamp.replace(microsecond=0),
                "status": submission.status,
                "invalid_reason_or_error": [],

                "urls": {
                    "self": submission_url,
                    "submission_group": obj['group_url'],
                    "submitted_files": _get_files_url(submission),
                    "autograder_test_case_results": (
                        _get_ag_test_results_url(submission)),
                    "student_test_suite_results": (
                        _get_suite_results_url(submission))
                }
            }

            actual_content = json_load_bytes(response.content)
            actual_content['timestamp'] = dateparse.parse_datetime(
                actual_content['timestamp']).replace(microsecond=0)
            self.assertEqual(expected_content, actual_content)

    def test_course_admin_or_semester_staff_get_other_user_submission(self):
        for user in self.admin, self.staff:
            client = MockClient(user)
            for obj in self.submission_objs:
                submission = Submission.objects.validate_and_create(
                    submitted_files=self.files_to_submit,
                    submission_group=obj['group']
                )

                submission_url = _get_submission_url(submission)
                response = client.get(submission_url)
                self.assertEqual(200, response.status_code)

                expected_content = {
                    "type": "submission",
                    "id": submission.pk,
                    "discarded_files": [],
                    "timestamp": submission.timestamp.replace(microsecond=0),
                    "status": submission.status,
                    "invalid_reason_or_error": [],

                    "urls": {
                        "self": submission_url,
                        "submission_group": obj['group_url'],
                        "submitted_files": _get_files_url(submission),
                        "autograder_test_case_results": (
                            _get_ag_test_results_url(submission)),
                        "student_test_suite_results": (
                            _get_suite_results_url(submission))
                    }
                }

            actual_content = json_load_bytes(response.content)
            actual_content['timestamp'] = dateparse.parse_datetime(
                actual_content['timestamp']).replace(microsecond=0)
            self.assertEqual(expected_content, actual_content)

    def test_student_get_other_submission_permission_denied(self):
        for user in self.enrolled, self.nobody:
            client = MockClient(user)
            for obj in self.submission_objs:
                if obj['user'] == user:
                    continue
                response = client.get(obj['submission_url'])
                self.assertEqual(403, response.status_code)

    def test_student_get_submission_project_hidden_permission_denied(self):
        self.project.visible_to_students = False
        self.project.validate_and_save()

        for obj in self.enrolled_submission_obj, self.nobody_submission_obj:
            client = MockClient(obj['user'])
            response = client.get(obj['submission_url'])
            self.assertEqual(403, response.status_code)

    def test_non_enrolled_student_non_public_project_get_submission_permission_denied(self):
        self.project.allow_submissions_from_non_enrolled_students = False
        self.project.validate_and_save()

        client = MockClient(self.nobody)
        response = client.get(self.nobody_submission_obj['submission_url'])
        self.assertEqual(403, response.status_code)


# -----------------------------------------------------------------------------
# -----------------------------------------------------------------------------


class ListSubmittedFilesEndpointTestCase(_SharedSetUp, TemporaryFilesystemTestCase):
    def setUp(self):
        super().setUp()

    def test_user_list_own_submitted_files(self):
        for obj in self.submission_objs:
            client = MockClient(obj['user'])
            response = client.get(obj['files_url'])
            self.assertEqual(200, response.status_code)

            expected_content = {
                "submitted_files": [
                    {
                        "filename": file_.name,
                        "url": _get_file_url(obj['submission'], file_.name)
                    }
                    for file_ in sorted(
                        self.files_to_submit, key=lambda f: f.name)
                ]
            }

            actual_content = json_load_bytes(response.content)
            actual_content['submitted_files'].sort(key=lambda f: f['filename'])

            self.assertEqual(expected_content, actual_content)

    def test_course_admin_or_semester_staff_list_other_user_submitted_files(self):
        for user in self.admin, self.staff:
            client = MockClient(user)
            for obj in self.submission_objs:
                response = client.get(obj['files_url'])
                self.assertEqual(200, response.status_code)

                expected_content = {
                    "submitted_files": [
                        {
                            "filename": file_.name,
                            "url": _get_file_url(obj['submission'], file_.name)
                        }
                        for file_ in sorted(
                            self.files_to_submit, key=lambda f: f.name)
                    ]
                }

                actual_content = json_load_bytes(response.content)
                actual_content['submitted_files'].sort(
                    key=lambda f: f['filename'])

                self.assertEqual(expected_content, actual_content)

    def test_student_list_other_user_submitted_files_permission_denied(self):
        for user in self.enrolled, self.nobody:
            client = MockClient(user)
            for obj in self.submission_objs:
                if obj['user'] == user:
                    continue

                response = client.get(obj['files_url'])
                self.assertEqual(403, response.status_code)

    def test_student_list_submitted_files_project_hidden_permission_denied(self):
        self.project.visible_to_students = False
        self.project.validate_and_save()

        for obj in self.enrolled_submission_obj, self.nobody_submission_obj:
            client = MockClient(obj['user'])
            response = client.get(obj['files_url'])

            self.assertEqual(403, response.status_code)

    def test_non_enrolled_student_non_public_project_list_submitted_files_permission_denied(self):
        self.project.allow_submissions_from_non_enrolled_students = False
        self.project.validate_and_save()

        client = MockClient(self.nobody)
        response = client.get(self.nobody_submission_obj['files_url'])

        self.assertEqual(403, response.status_code)

# -----------------------------------------------------------------------------


class GetSubmittedFileTestCase(_SharedSetUp, TemporaryFilesystemTestCase):
    def setUp(self):
        super().setUp()

        self.file_to_get = self.files_to_submit[0]
        for obj in self.submission_objs:
            obj['file_url'] = reverse(
                'submission:file',
                kwargs={'pk': obj['submission'].pk,
                        'filename': self.file_to_get.name})

    def test_valid_user_get_own_file(self):
        for obj in self.submission_objs:
            client = MockClient(obj['user'])
            response = client.get(obj['file_url'])

            self.assertEqual(200, response.status_code)

            self.file_to_get.seek(0)
            expected_content = {
                "type": "submitted_file",
                "filename": self.file_to_get.name,
                "size": self.file_to_get.size,
                "content": self.file_to_get.read().decode('utf-8'),

                "urls": {
                    "self": obj['file_url'],
                    "submission": obj['submission_url']
                }
            }

            self.assertEqual(
                expected_content, json_load_bytes(response.content))

    def test_course_admin_or_semester_staff_get_other_user_submitted_file(self):
        for user in self.staff, self.admin:
            client = MockClient(user)
            for obj in self.submission_objs:
                response = client.get(obj['file_url'])

                self.assertEqual(200, response.status_code)

                self.file_to_get.seek(0)
                expected_content = {
                    "type": "submitted_file",
                    "filename": self.file_to_get.name,
                    "size": self.file_to_get.size,
                    "content": self.file_to_get.read().decode('utf-8'),

                    "urls": {
                        "self": obj['file_url'],
                        "submission": obj['submission_url']
                    }
                }

                self.assertEqual(
                    expected_content, json_load_bytes(response.content))

    def test_student_get_other_submitted_file_permission_denied(self):
        for user in self.enrolled, self.nobody:
            client = MockClient(user)
            for obj in self.submission_objs:
                if obj['user'] == user:
                    continue
                response = client.get(obj['file_url'])

                self.assertEqual(403, response.status_code)

    def test_student_get_submitted_file_project_hidden_permission_denied(self):
        self.project.visible_to_students = False
        self.project.validate_and_save()

        for obj in self.enrolled_submission_obj, self.nobody_submission_obj:
            client = MockClient(obj['user'])
            response = client.get(obj['file_url'])

            self.assertEqual(403, response.status_code)

    def test_non_enrolled_student_non_public_project_get_submitted_files_permission_denied(self):
        self.project.allow_submissions_from_non_enrolled_students = False
        self.project.validate_and_save()

        client = MockClient(self.nobody)
        response = client.get(self.nobody_submission_obj['file_url'])

        self.assertEqual(403, response.status_code)

# -----------------------------------------------------------------------------
# -----------------------------------------------------------------------------


class ListAutograderTestCaseResultsTestCase(_SharedSetUp, TemporaryFilesystemTestCase):
    def setUp(self):
        super().setUp()

        self.visible_config = fbc.AutograderTestCaseFeedbackConfiguration(
            return_code_feedback_level=(
                fbc.ReturnCodeFeedbackLevel.correct_or_incorrect_only),
            visibility_level=fbc.VisibilityLevel.show_to_students)

        self.hidden_config = fbc.AutograderTestCaseFeedbackConfiguration(
            return_code_feedback_level=(
                fbc.ReturnCodeFeedbackLevel.correct_or_incorrect_only),
            visibility_level=fbc.VisibilityLevel.hide_from_students)

        self.points_for_test = 2

        self.visible_test = AutograderTestCaseFactory.validate_and_create(
            'compiled_and_run_test_case',
            name='visible', project=self.project,
            expected_return_code=0,
            points_for_correct_return_code=self.points_for_test,
            compiler='g++',
            student_files_to_compile_together=self.filenames_to_submit,
            student_resource_files=self.filenames_to_submit,
            executable_name='prog',
            feedback_configuration=self.visible_config)

        self.hidden_test = AutograderTestCaseFactory.validate_and_create(
            'compiled_and_run_test_case',
            name='hidden', project=self.project,
            expected_return_code=0,
            points_for_correct_return_code=self.points_for_test,
            compiler='g++',
            student_files_to_compile_together=self.filenames_to_submit,
            student_resource_files=self.filenames_to_submit,
            executable_name='prog',
            feedback_configuration=self.hidden_config)

        for obj in self.submission_objs:
            obj['test_results_url'] = _get_ag_test_results_url(
                obj['submission'])

            hidden_result = AutograderTestCaseResult.objects.create(
                test_case=self.hidden_test,
                submission=obj['submission'],
                compilation_return_code=0,
                return_code=0)

            visible_result = AutograderTestCaseResult.objects.create(
                test_case=self.visible_test,
                submission=obj['submission'],
                compilation_return_code=0,
                return_code=0)

            obj['hidden_result'] = hidden_result
            obj['visible_result'] = visible_result
            obj['test_results'] = sorted([hidden_result, visible_result],
                                         key=lambda res: res.test_case.name)

    def test_student_list_own_test_case_results_with_points_feedback(self):
        self.visible_test.feedback_configuration.points_feedback_level = (
            fbc.PointsFeedbackLevel.show_total)
        self.visible_test.validate_and_save()

        # make sure only results from visible tests are listed
        for obj in self.enrolled_submission_obj, self.nobody_submission_obj:
            client = MockClient(obj['user'])
            response = client.get(obj['test_results_url'])

            self.assertEqual(200, response.status_code)

            expected_content = {
                "autograder_test_case_results": [
                    {
                        "test_case_name": obj['visible_result'].test_case.name,
                        "points_awarded": self.points_for_test,
                        "points_possible": self.points_for_test,

                        "url": _get_ag_test_result_url(obj['visible_result'])
                    }
                ]
            }

            self.assertEqual(
                expected_content, json_load_bytes(response.content))

    def test_student_list_own_test_case_results_no_points_feedback(self):
        # make sure only results from visible tests are listed
        for obj in self.enrolled_submission_obj, self.nobody_submission_obj:
            client = MockClient(obj['user'])
            response = client.get(obj['test_results_url'])

            self.assertEqual(200, response.status_code)

            expected_content = {
                "autograder_test_case_results": [
                    {
                        "test_case_name": obj['visible_result'].test_case.name,

                        "url": _get_ag_test_result_url(obj['visible_result'])
                    }
                ]
            }

            self.assertEqual(
                expected_content, json_load_bytes(response.content))

    def test_course_admin_or_semester_staff_list_other_user_results(self):
        # should only see visible tests, but with max feedback
        for user in self.admin, self.staff:
            client = MockClient(user)
            for obj in self.submission_objs:
                if obj['user'] == user:
                    continue
                response = client.get(obj['test_results_url'])

                self.assertEqual(200, response.status_code)

                expected_content = {
                    "autograder_test_case_results": [
                        {
                            "test_case_name": (
                                obj['visible_result'].test_case.name),
                            "points_awarded": self.points_for_test,
                            "points_possible": self.points_for_test,

                            "url": _get_ag_test_result_url(
                                obj['visible_result'])
                        }
                    ]
                }

                self.assertEqual(
                    expected_content, json_load_bytes(response.content))

    def test_course_admin_or_semester_staff_get_own_results(self):
        # should see all test cases with max feedback
        for obj in self.admin_submission_obj, self.staff_submission_obj:
            client = MockClient(obj['user'])
            response = client.get(obj['test_results_url'])

            self.assertEqual(200, response.status_code)

            expected_content = {
                "autograder_test_case_results": [
                    {
                        "test_case_name": res.test_case.name,
                        "points_awarded": self.points_for_test,
                        "points_possible": self.points_for_test,

                        "url": _get_ag_test_result_url(res)
                    }
                    for res in obj['test_results']
                ]
            }

            self.assertEqual(
                expected_content, json_load_bytes(response.content))

    def test_post_deadline_feedback_override_show_hidden_test_hide_visible_test(self):
        self.visible_test.post_deadline_final_submission_feedback_configuration = (
            self.hidden_config
        )
        self.visible_test.validate_and_save()

        self.hidden_test.post_deadline_final_submission_feedback_configuration = (
            self.visible_config
        )
        self.hidden_test.validate_and_save()

        for user in self.admin, self.staff:
            for obj in (self.enrolled_submission_obj,
                        self.nobody_submission_obj):
                client = MockClient(user)
                expected_content = {
                    "autograder_test_case_results": [
                        {
                            "test_case_name": (
                                obj['hidden_result'].test_case.name),
                            "points_awarded": self.points_for_test,
                            "points_possible": self.points_for_test,
                            "url": _get_ag_test_result_url(obj['hidden_result'])
                        }
                    ]
                }

                response = client.get(obj['test_results_url'])
                self.assertEqual(200, response.status_code)
                self.assertEqual(
                    expected_content, json_load_bytes(response.content))

                (self.hidden_test.
                    post_deadline_final_submission_feedback_configuration.
                    points_feedback_level) = fbc.PointsFeedbackLevel.show_total
                self.hidden_test.validate_and_save()

                client = MockClient(obj['user'])
                response = client.get(obj['test_results_url'])
                self.assertEqual(200, response.status_code)
                self.assertEqual(
                    expected_content, json_load_bytes(response.content))

    def test_post_deadline_feedback_override_but_student_has_extension(self):
        self.visible_test.post_deadline_final_submission_feedback_configuration = (
            self.hidden_config
        )
        self.visible_test.validate_and_save()

        self.hidden_test.post_deadline_final_submission_feedback_configuration = (
            self.visible_config
        )
        self.hidden_test.validate_and_save()

        for obj in self.enrolled_submission_obj, self.nobody_submission_obj:
            obj['group'].extended_due_date = (
                timezone.now() + datetime.timedelta(minutes=1))
            obj['group'].save()

            expected_content = {
                "autograder_test_case_results": [
                    {
                        "test_case_name": (
                            obj['visible_result'].test_case.name),
                        "url": _get_ag_test_result_url(obj['visible_result'])
                    }
                ]
            }

            client = MockClient(obj['user'])
            response = client.get(obj['test_results_url'])
            self.assertEqual(200, response.status_code)
            self.assertEqual(
                expected_content, json_load_bytes(response.content))

            expected_content['autograder_test_case_results'][0].update({
                "points_awarded": self.points_for_test,
                "points_possible": self.points_for_test,
            })

            for user in self.admin, self.staff:
                client = MockClient(user)
                response = client.get(obj['test_results_url'])
                self.assertEqual(200, response.status_code)
                self.assertEqual(
                    expected_content, json_load_bytes(response.content))

    def test_post_deadline_feedback_override_but_not_final_submission(self):
        self.visible_test.post_deadline_final_submission_feedback_configuration = (
            self.hidden_config
        )
        self.visible_test.validate_and_save()

        self.hidden_test.post_deadline_final_submission_feedback_configuration = (
            self.visible_config
        )
        self.hidden_test.validate_and_save()

        for obj in self.enrolled_submission_obj, self.nobody_submission_obj:
            old_submission = Submission.objects.get(pk=obj['submission'].pk)
            new_submission = obj['submission']
            new_submission.pk = None
            new_submission.save()
            obj['submission'] = old_submission
            obj['submission'].group = obj['group']

            expected_content = {
                "autograder_test_case_results": [
                    {
                        "test_case_name": (
                            obj['visible_result'].test_case.name),
                        "url": _get_ag_test_result_url(obj['visible_result'])
                    }
                ]
            }

            client = MockClient(obj['user'])
            response = client.get(obj['test_results_url'])
            self.assertEqual(200, response.status_code)
            self.assertEqual(
                expected_content, json_load_bytes(response.content))

            expected_content['autograder_test_case_results'][0].update({
                "points_awarded": self.points_for_test,
                "points_possible": self.points_for_test,
            })

            for user in self.admin, self.staff:
                client = MockClient(user)
                response = client.get(obj['test_results_url'])
                self.assertEqual(200, response.status_code)
                self.assertEqual(
                    expected_content, json_load_bytes(response.content))

    def test_post_deadline_feedback_override_but_deadline_not_passed(self):
        self.visible_test.post_deadline_final_submission_feedback_configuration = (
            self.hidden_config
        )
        self.visible_test.validate_and_save()

        self.hidden_test.post_deadline_final_submission_feedback_configuration = (
            self.visible_config
        )
        self.hidden_test.validate_and_save()

        self.project.closing_time = (
            timezone.now() + datetime.timedelta(hours=1))
        self.project.validate_and_save()

        for obj in self.enrolled_submission_obj, self.nobody_submission_obj:
            expected_content = {
                "autograder_test_case_results": [
                    {
                        "test_case_name": (
                            obj['visible_result'].test_case.name),
                        "url": _get_ag_test_result_url(obj['visible_result'])
                    }
                ]
            }

            client = MockClient(obj['user'])
            response = client.get(obj['test_results_url'])
            self.assertEqual(200, response.status_code)
            self.assertEqual(
                expected_content, json_load_bytes(response.content))

            expected_content['autograder_test_case_results'][0].update({
                "points_awarded": self.points_for_test,
                "points_possible": self.points_for_test,
            })

            for user in self.admin, self.staff:
                client = MockClient(user)
                response = client.get(obj['test_results_url'])
                self.assertEqual(200, response.status_code)
                self.assertEqual(
                    expected_content, json_load_bytes(response.content))

    def test_student_list_other_user_results_permission_denied(self):
        for user in self.enrolled, self.nobody:
            client = MockClient(user)
            for obj in self.submission_objs:
                if obj['user'] == user:
                    continue
                response = client.get(obj['test_results_url'])
                self.assertEqual(403, response.status_code)

    def test_student_list_own_results_project_hidden_permission_denied(self):
        self.project.visible_to_students = False
        self.project.validate_and_save()

        for obj in self.enrolled_submission_obj, self.nobody_submission_obj:
            client = MockClient(obj['user'])
            response = client.get(obj['test_results_url'])
            self.assertEqual(403, response.status_code)

    def test_non_enrolled_student_non_public_project_list_results_permission_denied(self):
        self.project.allow_submissions_from_non_enrolled_students = False
        self.project.validate_and_save()

        client = MockClient(self.nobody)
        response = client.get(self.nobody_submission_obj['test_results_url'])
        self.assertEqual(403, response.status_code)


# -----------------------------------------------------------------------------
# -----------------------------------------------------------------------------


class ListStudentTestSuiteResultsTestCase(_SharedSetUp, TemporaryFilesystemTestCase):
    def setUp(self):
        super().setUp()

        self.maxDiff = None

        self.project.closing_time = (
            timezone.now() + timezone.timedelta(hours=-1))
        self.project.expected_student_file_patterns = [
            Project.FilePatternTuple('test_*.cpp', 0, 3)]
        proj_files = [
            SimpleUploadedFile('correct.cpp', b'blah'),
            SimpleUploadedFile('buggy1.cpp', b'buuug'),
            SimpleUploadedFile('buggy2.cpp', b'buuug')
        ]
        for file_ in proj_files:
            self.project.add_project_file(file_)

        self.points_per_buggy = 2
        self.points_for_suite = 4

        self.visible_config = fbc.StudentTestSuiteFeedbackConfiguration(
            visibility_level=fbc.VisibilityLevel.show_to_students,
            # points_feedback_level=fbc.PointsFeedbackLevel.show_breakdown,
            buggy_implementations_exposed_feedback_level=(
                (fbc.BuggyImplementationsExposedFeedbackLevel.
                    list_implementations_exposed_overall)))

        self.visible_suite = StudentTestSuiteFactory.validate_and_create(
            'compiled_student_test_suite',
            name='visible_suite',
            compiler='clang++',
            project=self.project,
            student_test_case_filename_pattern='test_*.cpp',
            correct_implementation_filename='correct.cpp',
            buggy_implementation_filenames=['buggy1.cpp', 'buggy2.cpp'],
            points_per_buggy_implementation_exposed=self.points_per_buggy,
            feedback_configuration=self.visible_config
        )

        self.hidden_config = fbc.StudentTestSuiteFeedbackConfiguration(
            visibility_level=fbc.VisibilityLevel.hide_from_students,
            # points_feedback_level=fbc.PointsFeedbackLevel.show_breakdown,
            buggy_implementations_exposed_feedback_level=(
                (fbc.BuggyImplementationsExposedFeedbackLevel.
                    list_implementations_exposed_overall)))

        self.hidden_suite = StudentTestSuiteFactory.validate_and_create(
            'compiled_student_test_suite',
            name='hidden_suite',
            compiler='clang++',
            project=self.project,
            student_test_case_filename_pattern='test_*.cpp',
            buggy_implementation_filenames=['buggy1.cpp', 'buggy2.cpp'],
            correct_implementation_filename='correct.cpp',
            points_per_buggy_implementation_exposed=self.points_per_buggy,
            feedback_configuration=self.hidden_config
        )

        for obj in self.submission_objs:
            visible_suite_result = StudentTestSuiteResult.objects.create(
                test_suite=self.visible_suite,
                submission=obj['submission'],
                buggy_implementations_exposed=['buggy1.cpp', 'buggy2.cpp'])

            hidden_suite_result = StudentTestSuiteResult.objects.create(
                test_suite=self.hidden_suite,
                submission=obj['submission'],
                buggy_implementations_exposed=['buggy1.cpp', 'buggy2.cpp'])

            obj['visible_result'] = visible_suite_result
            obj['hidden_result'] = hidden_suite_result

            obj['suite_results'] = sorted(
                [visible_suite_result, hidden_suite_result],
                key=lambda res: res.test_suite.name)

            obj['suite_results_url'] = _get_suite_results_url(
                obj['submission'])

        self.override_show_test = (
            fbc.StudentTestSuiteFeedbackConfiguration(
                visibility_level=fbc.VisibilityLevel.show_to_students))
        self.override_hide_test = (
            fbc.StudentTestSuiteFeedbackConfiguration(
                visibility_level=fbc.VisibilityLevel.hide_from_students))

    def test_valid_student_list_suite_results_with_points_feedback(self):
        # only results from visible suites should be listed

        self.visible_suite.feedback_configuration.points_feedback_level = (
            fbc.PointsFeedbackLevel.show_total)
        self.visible_suite.validate_and_save()

        for obj in self.enrolled_submission_obj, self.nobody_submission_obj:
            client = MockClient(obj['user'])
            response = client.get(obj['suite_results_url'])

            self.assertEqual(200, response.status_code)

            expected_content = {
                "student_test_suite_results": [
                    {
                        "test_suite_name": (
                            obj['visible_result'].test_suite.name),
                        "points_awarded": self.points_for_suite,
                        "points_possible": self.points_for_suite,

                        "url": _get_suite_result_url(obj['visible_result'])
                    }
                ]
            }

            self.assertEqual(
                expected_content, json_load_bytes(response.content))

    def test_valid_student_list_suite_results_no_points_feedback(self):
        for obj in self.enrolled_submission_obj, self.nobody_submission_obj:
            client = MockClient(obj['user'])
            response = client.get(obj['suite_results_url'])

            self.assertEqual(200, response.status_code)

            expected_content = {
                "student_test_suite_results": [
                    {
                        "test_suite_name": (
                            obj['visible_result'].test_suite.name),

                        "url": _get_suite_result_url(obj['visible_result'])
                    }
                ]
            }

            self.assertEqual(
                expected_content, json_load_bytes(response.content))

    def test_course_admin_or_semester_staff_get_other_user_results(self):
        # should only see visible suites, with max feedback
        for user in self.admin, self.staff:
            client = MockClient(user)

            for obj in self.submission_objs:
                if obj['user'] == user:
                    continue
                response = client.get(obj['suite_results_url'])

                self.assertEqual(200, response.status_code)

                expected_content = {
                    "student_test_suite_results": [
                        {
                            "test_suite_name": (
                                obj['visible_result'].test_suite.name),
                            "points_awarded": self.points_for_suite,
                            "points_possible": self.points_for_suite,

                            "url": _get_suite_result_url(obj['visible_result'])
                        }
                    ]
                }

                self.assertEqual(
                    expected_content, json_load_bytes(response.content))

    def test_course_admin_or_semester_staff_get_own_results(self):
        # should see all suites
        for obj in self.admin_submission_obj, self.staff_submission_obj:
            client = MockClient(obj['user'])
            response = client.get(obj['suite_results_url'])

            self.assertEqual(200, response.status_code)

            expected_content = {
                "student_test_suite_results": [
                    {
                        "test_suite_name": res.test_suite.name,
                        "points_awarded": self.points_for_suite,
                        "points_possible": self.points_for_suite,

                        "url": _get_suite_result_url(res)
                    }
                    for res in sorted(
                        obj['suite_results'], key=lambda r: r.test_suite.name)
                ]
            }

            actual_content = json_load_bytes(response.content)
            actual_content['student_test_suite_results'].sort(
                key=lambda r: r['test_suite_name'])
            self.assertEqual(expected_content, actual_content)

    def test_post_deadline_feedback_override_show_hidden_suite_hide_visible_suite(self):
        self.visible_suite.post_deadline_final_submission_feedback_configuration = (
            self.hidden_config
        )
        self.visible_suite.validate_and_save()

        self.hidden_suite.post_deadline_final_submission_feedback_configuration = (
            self.visible_config
        )
        self.hidden_suite.validate_and_save()

        for user in self.admin, self.staff:
            for obj in (self.enrolled_submission_obj,
                        self.nobody_submission_obj):
                client = MockClient(user)
                expected_content = {
                    "student_test_suite_results": [
                        {
                            "test_suite_name": (
                                obj['hidden_result'].test_suite.name),
                            "points_awarded": self.points_for_suite,
                            "points_possible": self.points_for_suite,
                            "url": _get_suite_result_url(obj['hidden_result'])
                        }
                    ]
                }

                response = client.get(obj['suite_results_url'])
                self.assertEqual(200, response.status_code)
                self.assertEqual(
                    expected_content, json_load_bytes(response.content))

                (self.hidden_suite.
                    post_deadline_final_submission_feedback_configuration.
                    points_feedback_level) = fbc.PointsFeedbackLevel.show_total
                self.hidden_suite.validate_and_save()

                client = MockClient(obj['user'])
                response = client.get(obj['suite_results_url'])
                self.assertEqual(200, response.status_code)
                self.assertEqual(
                    expected_content, json_load_bytes(response.content))

    def test_post_deadline_feedback_override_but_student_has_extension(self):
        self.visible_suite.post_deadline_final_submission_feedback_configuration = (
            self.hidden_config
        )
        self.visible_suite.validate_and_save()

        self.hidden_suite.post_deadline_final_submission_feedback_configuration = (
            self.visible_config
        )
        self.hidden_suite.validate_and_save()

        for obj in self.enrolled_submission_obj, self.nobody_submission_obj:
            obj['group'].extended_due_date = (
                timezone.now() + datetime.timedelta(minutes=1))
            obj['group'].save()

            expected_content = {
                "student_test_suite_results": [
                    {
                        "test_suite_name": (
                            obj['visible_result'].test_suite.name),
                        "url":  _get_suite_result_url(obj['visible_result'])
                    }
                ]
            }

            client = MockClient(obj['user'])
            response = client.get(obj['suite_results_url'])
            self.assertEqual(200, response.status_code)
            self.assertEqual(
                expected_content, json_load_bytes(response.content))

            expected_content['student_test_suite_results'][0].update({
                "points_awarded": self.points_for_suite,
                "points_possible": self.points_for_suite,
            })

            for user in self.admin, self.staff:
                client = MockClient(user)
                response = client.get(obj['suite_results_url'])
                self.assertEqual(200, response.status_code)
                self.assertEqual(
                    expected_content, json_load_bytes(response.content))

    def test_post_deadline_feedback_override_but_not_final_submission(self):
        self.visible_suite.post_deadline_final_submission_feedback_configuration = (
            self.hidden_config
        )
        self.visible_suite.validate_and_save()

        self.hidden_suite.post_deadline_final_submission_feedback_configuration = (
            self.visible_config
        )
        self.hidden_suite.validate_and_save()

        for obj in self.enrolled_submission_obj, self.nobody_submission_obj:
            old_submission = Submission.objects.get(pk=obj['submission'].pk)
            new_submission = obj['submission']
            new_submission.pk = None
            new_submission.save()
            obj['submission'] = old_submission
            obj['submission'].group = obj['group']

            expected_content = {
                "student_test_suite_results": [
                    {
                        "test_suite_name": (
                            obj['visible_result'].test_suite.name),
                        "url": _get_suite_result_url(obj['visible_result'])
                    }
                ]
            }

            client = MockClient(obj['user'])
            response = client.get(obj['suite_results_url'])
            self.assertEqual(200, response.status_code)
            self.assertEqual(
                expected_content, json_load_bytes(response.content))

            expected_content['student_test_suite_results'][0].update({
                "points_awarded": self.points_for_suite,
                "points_possible": self.points_for_suite,
            })

            for user in self.admin, self.staff:
                client = MockClient(user)
                response = client.get(obj['suite_results_url'])
                self.assertEqual(200, response.status_code)
                self.assertEqual(
                    expected_content, json_load_bytes(response.content))

    def test_post_deadline_feedback_override_but_deadline_not_passed(self):
        self.visible_suite.post_deadline_final_submission_feedback_configuration = (
            self.hidden_config
        )
        self.visible_suite.validate_and_save()

        self.hidden_suite.post_deadline_final_submission_feedback_configuration = (
            self.visible_config
        )
        self.hidden_suite.validate_and_save()

        self.project.closing_time = (
            timezone.now() + datetime.timedelta(hours=1))
        self.project.validate_and_save()

        for obj in self.enrolled_submission_obj, self.nobody_submission_obj:
            expected_content = {
                "student_test_suite_results": [
                    {
                        "test_suite_name": (
                            obj['visible_result'].test_suite.name),
                        "url": _get_suite_result_url(obj['visible_result'])
                    }
                ]
            }

            client = MockClient(obj['user'])
            response = client.get(obj['suite_results_url'])
            self.assertEqual(200, response.status_code)
            self.assertEqual(
                expected_content, json_load_bytes(response.content))

            expected_content['student_test_suite_results'][0].update({
                "points_awarded": self.points_for_suite,
                "points_possible": self.points_for_suite,
            })

            for user in self.admin, self.staff:
                client = MockClient(user)
                response = client.get(obj['suite_results_url'])
                self.assertEqual(200, response.status_code)
                self.assertEqual(
                    expected_content, json_load_bytes(response.content))

    def test_student_list_other_user_results_permission_denied(self):
        for user in self.enrolled, self.nobody:
            client = MockClient(user)

            for obj in self.submission_objs:
                if obj['user'] == user:
                    continue
                response = client.get(obj['suite_results_url'])

                self.assertEqual(403, response.status_code)

    def test_student_list_own_results_project_hidden_permission_denied(self):
        self.project.visible_to_students = False
        self.project.validate_and_save()

        for obj in self.enrolled_submission_obj, self.nobody_submission_obj:
            client = MockClient(obj['user'])
            response = client.get(obj['suite_results_url'])
            self.assertEqual(403, response.status_code)

    def test_non_enrolled_student_non_public_project_list_results_permission_denied(self):
        self.project.allow_submissions_from_non_enrolled_students = False
        self.project.validate_and_save()
        client = MockClient(self.nobody)
        response = client.get(self.nobody_submission_obj['suite_results_url'])
        self.assertEqual(403, response.status_code)
