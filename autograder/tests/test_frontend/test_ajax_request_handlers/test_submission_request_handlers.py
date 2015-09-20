import datetime

from django.core.files.uploadedfile import SimpleUploadedFile
from django.core.exceptions import ObjectDoesNotExist
from django.test import RequestFactory
from django.core.urlresolvers import resolve
from django.utils import timezone

import autograder.tests.dummy_object_utils as obj_ut

from .utils import (
    process_get_request,
    process_patch_request, json_load_bytes, RequestHandlerTestCase)

from autograder.frontend.json_api_serializers import submission_to_json

from autograder.models import (
    SubmissionGroup, AutograderTestCaseFactory, Submission,
    AutograderTestCaseResultBase)
from autograder.models.fields import FeedbackConfiguration


class _SetUpBase(RequestHandlerTestCase):
    def setUp(self):
        super().setUp()

        self.maxDiff = None

        self.admin = obj_ut.create_dummy_users()
        self.staff = obj_ut.create_dummy_users()
        self.enrolled = obj_ut.create_dummy_users()
        self.nobody = obj_ut.create_dummy_users()

        self.course = obj_ut.create_dummy_courses()
        self.semester = obj_ut.create_dummy_semesters(self.course)

        self.course.add_course_admins(self.admin)
        self.semester.add_semester_staff(self.staff)
        self.semester.add_enrolled_students(self.enrolled)

        feedback_config = FeedbackConfiguration(
            return_code_feedback_level='correct_or_incorrect_only')

        self.project = obj_ut.create_dummy_projects(self.semester)
        self.project.required_student_files = ['hello.cpp']
        self.project.feedback_config = feedback_config
        self.project.save()

        self.visible_test = AutograderTestCaseFactory.validate_and_create(
            'compiled_test_case',
            name='visible', project=self.project,
            hide_from_students=False,
            expected_return_code=0,
            points_for_correct_return_code=2,
            compiler='g++',
            files_to_compile_together=['hello.cpp'],
            student_resource_files=['hello.cpp'],
            executable_name='prog')

        self.hidden_test = AutograderTestCaseFactory.validate_and_create(
            'compiled_test_case',
            name='hidden', project=self.project,
            hide_from_students=True,
            expected_return_code=0,
            points_for_correct_return_code=2,
            compiler='g++',
            files_to_compile_together=['hello.cpp'],
            student_resource_files=['hello.cpp'],
            executable_name='prog')
        # self.hidden_test.pk = None
        # self.hidden_test.name = 'hidden'
        # self.hidden_test.validate_and_save()

        self.assertNotEqual(self.visible_test, self.hidden_test)

        self.files = [
            SimpleUploadedFile('hello.cpp', b'int main() { return 0; }')
        ]

        self.visible_result = AutograderTestCaseResultBase.objects.create(
            test_case=self.visible_test,
            return_code=0)

        self.hidden_result = AutograderTestCaseResultBase.objects.create(
            test_case=self.hidden_test,
            return_code=0)


class AddSubmissionRequestTestCase(_SetUpBase):
    def setUp(self):
        super().setUp()

        self.maxDiff = None

    def test_valid_student_submit(self):
        group = SubmissionGroup.objects.validate_and_create(
            members=[self.enrolled.username], project=self.project)

        response = _add_submission_request(
            self.files, group.pk, self.enrolled)

        self.assertEqual(201, response.status_code)

        loaded = Submission.objects.get(submission_group__pk=group.pk)
        expected = {
            'data': submission_to_json(loaded)
        }

        actual = json_load_bytes(response.content)

        self.assertJSONObjsEqual(expected, actual)

    def test_valid_staff_or_admin_submit(self):
        # Feedback configuration should be set to max automatically.
        for user in (self.admin, self.staff):
            group = SubmissionGroup.objects.validate_and_create(
                members=[user.username], project=self.project)

            response = _add_submission_request(
                self.files, group.pk, user)

            self.assertEqual(201, response.status_code)

            loaded = Submission.objects.get(submission_group__pk=group.pk)
            expected = {
                'data': submission_to_json(loaded)
            }

            expected['data']['attributes'][
                'test_case_feedback_config_override'] = (
                    FeedbackConfiguration.get_max_feedback().to_json())

            actual = json_load_bytes(response.content)

            self.assertJSONObjsEqual(expected, actual)

    def test_invalid_user_not_in_group(self):
        new_user = obj_ut.create_dummy_users()
        self.semester.add_enrolled_students(new_user)
        group = SubmissionGroup.objects.validate_and_create(
            members=[self.enrolled.username], project=self.project)

        response = _add_submission_request(self.files, group.pk, new_user)

        self.assertEqual(403, response.status_code)

    def test_group_not_found(self):
        response = _add_submission_request(self.files, 42, self.enrolled)

        self.assertEqual(404, response.status_code)

    def test_invalid_already_has_submit_in_queue(self):
        self.project.allow_submissions_from_non_enrolled_students = True
        self.project.validate_and_save()
        for user in (self.admin, self.staff, self.enrolled, self.nobody):
            group = SubmissionGroup.objects.validate_and_create(
                members=[user.username], project=self.project)
            response = _add_submission_request(self.files, group.pk, user)
            self.assertEqual(201, response.status_code)

            response = _add_submission_request(self.files, group.pk, user)
            self.assertEqual(409, response.status_code)

            # Throws an exception if more than 1 submission
            # exists for the group
            Submission.objects.get(submission_group=group)

            self.assertTrue('errors' in json_load_bytes(response.content))

    def test_error_project_deadline_passed(self):
        self.project.allow_submissions_from_non_enrolled_students = True
        self.project.closing_time = (
            timezone.now() + datetime.timedelta(minutes=-1))
        self.project.validate_and_save()

        for user in (self.enrolled, self.nobody):
            group = SubmissionGroup.objects.validate_and_create(
                members=[user.username], project=self.project)
            response = _add_submission_request(self.files, group.pk, user)
            self.assertEqual(409, response.status_code)
            with self.assertRaises(ObjectDoesNotExist):
                Submission.objects.get(submission_group=group)
            self.assertTrue('errors' in json_load_bytes(response.content))

    def test_no_error_project_deadline_passed_but_group_has_extension(self):
        self.project.allow_submissions_from_non_enrolled_students = True
        self.project.closing_time = (
            timezone.now() + datetime.timedelta(minutes=-1))
        self.project.validate_and_save()

        extension = self.project.closing_time + datetime.timedelta(days=1)
        for user in (self.enrolled, self.nobody):
            group = SubmissionGroup.objects.validate_and_create(
                members=[user.username], project=self.project,
                extended_due_date=extension)
            response = _add_submission_request(self.files, group.pk, user)
            self.assertEqual(201, response.status_code)

    def test_error_project_deadline_and_extension_passed(self):
        self.project.allow_submissions_from_non_enrolled_students = True
        self.project.closing_time = (
            timezone.now() + datetime.timedelta(days=-1))
        self.project.validate_and_save()

        extension = timezone.now() + datetime.timedelta(minutes=-1)
        for user in (self.enrolled, self.nobody):
            group = SubmissionGroup.objects.validate_and_create(
                members=[user.username], project=self.project,
                extended_due_date=extension)
            response = _add_submission_request(self.files, group.pk, user)
            self.assertEqual(409, response.status_code)
            with self.assertRaises(ObjectDoesNotExist):
                Submission.objects.get(submission_group=group)

    def test_no_error_admin_or_staff_submit_passed_deadline(self):
        self.project.closing_time = (
            timezone.now() + datetime.timedelta(minutes=-1))
        self.project.validate_and_save()

        for user in (self.admin, self.staff):
            group = SubmissionGroup.objects.validate_and_create(
                members=[user.username], project=self.project)
            response = _add_submission_request(self.files, group.pk, user)
            self.assertEqual(201, response.status_code)

            # There should be exactly one submission for the group
            Submission.objects.get(submission_group=group)

    def test_error_student_submissions_disallowed(self):
        self.project.allow_submissions_from_non_enrolled_students = True
        self.project.disallow_student_submissions = True
        self.project.validate_and_save()

        for user in (self.enrolled, self.nobody):
            group = SubmissionGroup.objects.validate_and_create(
                members=[user.username], project=self.project)
            response = _add_submission_request(self.files, group.pk, user)
            self.assertEqual(409, response.status_code)
            with self.assertRaises(ObjectDoesNotExist):
                Submission.objects.get(submission_group=group)


def _add_submission_request(files, submission_group_id, user):
    url = '/submissions/submission/'
    data = {'files': files, 'submission_group_id': submission_group_id}

    request = RequestFactory().post(url, data)
    request.user = user

    resolved = resolve(request.path)
    return resolved.func(request, *resolved.args, **resolved.kwargs)


# -----------------------------------------------------------------------------


class GetSubmissionRequestTestCase(_SetUpBase):
    def test_student_get_own_submit(self):
        group = SubmissionGroup.objects.validate_and_create(
            members=[self.enrolled.username], project=self.project)
        submission = Submission.objects.validate_and_create(
            submission_group=group, submitted_files=self.files)
        submission.results.add(self.visible_result, self.hidden_result)

        submission.test_case_feedback_config_override = FeedbackConfiguration(
            return_code_feedback_level='correct_or_incorrect_only')
        submission.save()

        response = _get_submission_request(submission.pk, self.enrolled)
        self.assertEqual(200, response.status_code)

        # No points feedback
        expected = {
            'data': submission_to_json(submission),
            'meta': {
                'results': [
                    self.visible_result.to_json(),
                ]
            }
        }
        actual = json_load_bytes(response.content)
        self.assertJSONObjsEqual(expected, actual)

        # Show points total, override at submission level
        submission.test_case_feedback_config_override = (
            self.project.test_case_feedback_configuration)
        submission.test_case_feedback_config_override.points_feedback_level = (
            'show_total')
        submission.save()

        response = _get_submission_request(submission.pk, self.enrolled)
        self.assertEqual(200, response.status_code)

        expected = {
            'data': submission_to_json(submission),
            'meta': {
                'results': [
                    self.visible_result.to_json(),
                ],
                'total_points_awarded': (
                    self.visible_result.to_json()['total_points_awarded']),
                'total_points_possible': (
                    self.visible_result.to_json()['total_points_possible'])
            }
        }

        actual = json_load_bytes(response.content)
        self.assertJSONObjsEqual(expected, actual)

        # Show points total, set at project level
        submission.test_case_feedback_config_override = None
        submission.save()
        self.project.test_case_feedback_configuration.points_feedback_level = (
            'show_total')
        self.project.validate_and_save()

        expected['data'] = submission_to_json(submission)

        response = _get_submission_request(submission.pk, self.enrolled)
        self.assertEqual(200, response.status_code)

        actual = json_load_bytes(response.content)
        self.assertJSONObjsEqual(expected, actual)

    def test_admin_or_staff_get_student_submit(self):
        # Should get max feedback on visible test cases
        group = SubmissionGroup.objects.validate_and_create(
            members=[self.enrolled.username], project=self.project)
        for user in (self.admin, self.staff):
            submission = Submission.objects.validate_and_create(
                submission_group=group, submitted_files=self.files)
            submission.results.add(self.visible_result, self.hidden_result)

            response = _get_submission_request(submission.pk, user)
            self.assertEqual(200, response.status_code)

            expected = {
                'data': submission_to_json(submission),
                'meta': {
                    'results': [
                        self.visible_result.to_json(
                            FeedbackConfiguration.get_max_feedback())
                    ],
                    'total_points_possible': self.visible_result.to_json(
                        FeedbackConfiguration.get_max_feedback()
                        )['total_points_possible'],
                    'total_points_awarded': self.visible_result.to_json(
                        FeedbackConfiguration.get_max_feedback()
                        )['total_points_awarded']
                }
            }

            actual = json_load_bytes(response.content)

            self.assertJSONObjsEqual(expected, actual)

    def test_admin_or_staff_get_own_submit(self):
        # Should get max feedback on ALL test cases
        for user in (self.admin, self.staff):
            group = SubmissionGroup.objects.validate_and_create(
                members=[user.username], project=self.project)
            submission = Submission.objects.validate_and_create(
                submission_group=group, submitted_files=self.files)
            submission.results.add(self.visible_result, self.hidden_result)

            response = _get_submission_request(submission.pk, user)
            self.assertEqual(200, response.status_code)

            sort_key = lambda obj: obj['test_name']
            results_json = list(sorted([
                self.visible_result.to_json(
                    FeedbackConfiguration.get_max_feedback()),
                self.hidden_result.to_json(
                    FeedbackConfiguration.get_max_feedback())
            ], key=sort_key))

            pts_possible = sum(
                result['total_points_possible'] for result in results_json)

            pts_awarded = sum(
                result['total_points_awarded'] for result in results_json)

            expected = {
                'data': submission_to_json(submission),
                'meta': {
                    'results': results_json,
                    'total_points_possible': pts_possible,
                    'total_points_awarded': pts_awarded
                }
            }

            actual = json_load_bytes(response.content)
            actual['meta']['results'].sort(key=sort_key)

            self.assertJSONObjsEqual(expected, actual)

    def test_show_all_tests_override_for_student(self):
        group = SubmissionGroup.objects.validate_and_create(
            members=[self.enrolled.username], project=self.project)
        submission = Submission.objects.validate_and_create(
            submission_group=group, submitted_files=self.files)
        submission.results.add(self.visible_result, self.hidden_result)

        submission.show_all_test_cases = True
        submission.save()

        response = _get_submission_request(submission.pk, self.enrolled)
        self.assertEqual(200, response.status_code)

        sort_key = lambda obj: obj['test_name']
        expected = {
            'data': submission_to_json(submission),
            'meta': {
                'results': list(sorted([
                    self.visible_result.to_json(),
                    self.hidden_result.to_json()
                ], key=sort_key))
            }
        }

        actual = json_load_bytes(response.content)
        actual['meta']['results'].sort(key=sort_key)

        self.assertJSONObjsEqual(expected, actual)

    def test_show_all_tests_override_staff_view_student_submission(self):
        group = SubmissionGroup.objects.validate_and_create(
            members=[self.enrolled.username], project=self.project)
        submission = Submission.objects.validate_and_create(
            submission_group=group, submitted_files=self.files)
        submission.results.add(self.visible_result, self.hidden_result)

        submission.show_all_test_cases = True
        submission.save()

        response = _get_submission_request(submission.pk, self.staff)
        self.assertEqual(200, response.status_code)

        sort_key = lambda obj: obj['test_name']
        results_json = list(sorted([
            self.visible_result.to_json(
                FeedbackConfiguration.get_max_feedback()),
            self.hidden_result.to_json(
                FeedbackConfiguration.get_max_feedback())
        ], key=sort_key))

        pts_possible = sum(
            result['total_points_possible'] for result in results_json)

        pts_awarded = sum(
            result['total_points_awarded'] for result in results_json)

        expected = {
            'data': submission_to_json(submission),
            'meta': {
                'results': results_json,
                'total_points_awarded': pts_awarded,
                'total_points_possible': pts_possible
            }
        }

        actual = json_load_bytes(response.content)
        actual['meta']['results'].sort(key=sort_key)

        self.assertJSONObjsEqual(expected, actual)

    def test_permission_denied(self):
        new_user = obj_ut.create_dummy_users()
        self.semester.add_enrolled_students(new_user)

        group = SubmissionGroup.objects.validate_and_create(
            members=[self.enrolled.username], project=self.project)
        submission = Submission.objects.validate_and_create(
            submission_group=group, submitted_files=self.files)

        response = _get_submission_request(submission.pk, new_user)
        self.assertEqual(403, response.status_code)


def _get_submission_request(submission_id, user):
    url = '/submissions/submission/{}/'.format(submission_id)
    return process_get_request(url, user)


# -----------------------------------------------------------------------------

class PatchSubmissionRequestTestCase(_SetUpBase):
    def setUp(self):
        super().setUp()

        self.group = SubmissionGroup.objects.validate_and_create(
            members=[self.enrolled.username], project=self.project)
        self.submission = Submission.objects.validate_and_create(
            submission_group=self.group, submitted_files=self.files)

    def test_admin_override_feedback_for_student(self):
        response = _patch_submission_request(
            self.submission.pk,
            FeedbackConfiguration.get_max_feedback().to_json(),
            self.admin,
            new_show_tests=True)

        self.assertEqual(204, response.status_code)

        loaded = Submission.objects.get(pk=self.submission.pk)

        self.assertEqual(loaded.test_case_feedback_config_override,
                         FeedbackConfiguration.get_max_feedback())
        self.assertTrue(loaded.show_all_test_cases)

    def test_bad_feedback_config(self):
        response = _patch_submission_request(
            self.submission.pk,
            {'return_code_feedback_level': 'spam'},
            self.admin)

        self.assertEqual(400, response.status_code)

    def test_submission_not_found(self):
        response = _patch_submission_request(
            42,
            FeedbackConfiguration.get_max_feedback().to_json(),
            self.admin)

        self.assertEqual(404, response.status_code)

    def test_permission_denied(self):
        new_user = obj_ut.create_dummy_users()
        self.semester.add_enrolled_students(new_user)

        for user in (new_user, self.nobody, self.enrolled):
            response = _patch_submission_request(
                self.submission.pk,
                FeedbackConfiguration.get_max_feedback().to_json(),
                user)
            self.assertEqual(403, response.status_code)


def _patch_submission_request(submission_id, new_feedback, user,
                              new_show_tests=None):
    url = '/submissions/submission/{}/'.format(submission_id)
    data = {
        'data': {
            'type': 'submission',
            'id': submission_id,
            'attributes': {
                'test_case_feedback_config_override': new_feedback
            }
        }
    }
    if new_show_tests is not None:
        data['data']['attributes']['show_all_test_cases'] = new_show_tests

    return process_patch_request(url, data, user)


# -----------------------------------------------------------------------------

class GetSubmittedFileRequestTestCase(_SetUpBase):
    def setUp(self):
        super().setUp()

        self.group = SubmissionGroup.objects.validate_and_create(
            members=[self.enrolled.username], project=self.project)
        self.submission = Submission.objects.validate_and_create(
            submission_group=self.group, submitted_files=self.files)

    def test_valid_view_file(self):
        for user in (self.enrolled, self.staff, self.admin):
            file_ = self.files[0]
            response = _get_submitted_file_request(
                self.submission.pk, file_.name, user)

            self.assertEqual(200, response.status_code)
            # self.assertEqual('text/plain', response.content_type)

            file_.seek(0)
            self.assertEqual(
                file_.read(), response.content) #b''.join(response.streaming_content))

    def test_file_not_found(self):
        response = _get_submitted_file_request(
            self.submission.pk, 'not_a_file', self.enrolled)
        self.assertEqual(404, response.status_code)

    def test_submission_not_found(self):
        response = _get_submitted_file_request(
            42, self.files[0].name, self.enrolled)
        self.assertEqual(404, response.status_code)

    def test_permission_denied(self):
        new_user = obj_ut.create_dummy_users()
        self.semester.add_enrolled_students(new_user)
        for user in (new_user, self.nobody):
            response = _get_submitted_file_request(
                self.submission.pk, self.files[0].name, user)

            self.assertEqual(403, response.status_code)


def _get_submitted_file_request(submission_id, filename, user):
    url = '/submissions/submission/{}/file/{}/'.format(submission_id, filename)
    return process_get_request(url, user)
