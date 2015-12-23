import itertools

from django.core.urlresolvers import reverse

from autograder.core.tests.temporary_filesystem_test_case import (
    TemporaryFilesystemTestCase)
import autograder.core.tests.dummy_object_utils as obj_ut
from .utilities import MockClient, json_load_bytes, sorted_by_pk


class GetUpdateDeleteSubmissionGroupTestCase(TemporaryFilesystemTestCase):
    def setUp(self):
        super().setUp()

    def test_user_get_own_group(self):
        self.fail()

    def test_course_admin_or_semester_staff_get_student_group(self):
        self.fail()

    def test_student_get_other_group_permission_denied(self):
        self.fail()

    def test_get_submission_group_user_cannot_view_project_permission_denied(self):
        self.fail()

    # -------------------------------------------------------------------------

    def test_course_admin_or_semester_staff_edit_group(self):
        self.fail()

    def test_other_edit_group_permission_denied(self):
        self.fail()

    # -------------------------------------------------------------------------

    def test_course_admin_or_semester_staff_delete_group(self):
        self.fail()

    def test_other_delete_group_permission_denied(self):
        self.fail()

# -----------------------------------------------------------------------------
# -----------------------------------------------------------------------------


class ListAddSubmissionTestCase(TemporaryFilesystemTestCase):
    def setUp(self):
        super().setUp()

    def test_user_list_own_submissions(self):
        self.fail()

    def test_course_admin_or_semester_staff_list_student_submissions(self):
        self.fail()

    def test_non_admin_non_staff_list_other_submissions_permission_denied(self):
        self.fail()

    def test_list_submissions_student_cannot_view_project_permission_denied(self):
        self.fail()

    # -------------------------------------------------------------------------

    # def test_valid_student_staff_or_admin_submit(self):
    #     for user in (self.enrolled, self.admin, self.staff):
    #         group = SubmissionGroup.objects.validate_and_create(
    #             members=[user.username], project=self.project)

    #         response = _add_submission_request(
    #             self.files, group.pk, user)

    #         self.assertEqual(201, response.status_code)

    #         loaded = Submission.objects.get(submission_group__pk=group.pk)
    #         expected = {
    #             'data': submission_to_json(loaded)
    #         }

    #         actual = json_load_bytes(response.content)

    #         self.assertJSONObjsEqual(expected, actual)

    # def test_permission_denied_user_not_in_group(self):
    #     new_user = obj_ut.create_dummy_user()
    #     self.semester.add_enrolled_students(new_user)
    #     group = SubmissionGroup.objects.validate_and_create(
    #         members=[self.enrolled.username], project=self.project)

    #     response = _add_submission_request(self.files, group.pk, new_user)

    #     self.assertEqual(403, response.status_code)

    # def test_group_not_found(self):
    #     response = _add_submission_request(self.files, 42, self.enrolled)

    #     self.assertEqual(404, response.status_code)

    # def test_invalid_already_has_submit_in_queue(self):
    #     for user in (self.admin, self.staff, self.enrolled, self.nobody):
    #         group = SubmissionGroup.objects.validate_and_create(
    #             members=[user.username], project=self.project)
    #         response = _add_submission_request(self.files, group.pk, user)
    #         self.assertEqual(201, response.status_code)

    #         response = _add_submission_request(self.files, group.pk, user)
    #         self.assertEqual(409, response.status_code)

    #         # Throws an exception if more than 1 submission
    #         # exists for the group
    #         Submission.objects.get(submission_group=group)

    #         self.assertTrue('errors' in json_load_bytes(response.content))

    # def test_error_project_deadline_passed(self):
    #     self.project.allow_submissions_from_non_enrolled_students = True
    #     self.project.closing_time = (
    #         timezone.now() + datetime.timedelta(minutes=-1))
    #     self.project.validate_and_save()

    #     for user in (self.enrolled, self.nobody):
    #         group = SubmissionGroup.objects.validate_and_create(
    #             members=[user.username], project=self.project)
    #         response = _add_submission_request(self.files, group.pk, user)
    #         self.assertEqual(409, response.status_code)
    #         with self.assertRaises(ObjectDoesNotExist):
    #             Submission.objects.get(submission_group=group)
    #         self.assertTrue('errors' in json_load_bytes(response.content))

    # def test_no_error_project_deadline_passed_but_group_has_extension(self):
    #     self.project.allow_submissions_from_non_enrolled_students = True
    #     self.project.closing_time = (
    #         timezone.now() + datetime.timedelta(minutes=-1))
    #     self.project.validate_and_save()

    #     extension = self.project.closing_time + datetime.timedelta(days=1)
    #     for user in (self.enrolled, self.nobody):
    #         group = SubmissionGroup.objects.validate_and_create(
    #             members=[user.username], project=self.project,
    #             extended_due_date=extension)
    #         response = _add_submission_request(self.files, group.pk, user)
    #         self.assertEqual(201, response.status_code)

    # def test_error_project_deadline_and_extension_passed(self):
    #     self.project.allow_submissions_from_non_enrolled_students = True
    #     self.project.closing_time = (
    #         timezone.now() + datetime.timedelta(days=-1))
    #     self.project.validate_and_save()

    #     extension = timezone.now() + datetime.timedelta(minutes=-1)
    #     for user in (self.enrolled, self.nobody):
    #         group = SubmissionGroup.objects.validate_and_create(
    #             members=[user.username], project=self.project,
    #             extended_due_date=extension)
    #         response = _add_submission_request(self.files, group.pk, user)
    #         self.assertEqual(409, response.status_code)
    #         with self.assertRaises(ObjectDoesNotExist):
    #             Submission.objects.get(submission_group=group)

    # def test_no_error_admin_or_staff_submit_passed_deadline(self):
    #     self.project.closing_time = (
    #         timezone.now() + datetime.timedelta(minutes=-1))
    #     self.project.validate_and_save()

    #     for user in (self.admin, self.staff):
    #         group = SubmissionGroup.objects.validate_and_create(
    #             members=[user.username], project=self.project)
    #         response = _add_submission_request(self.files, group.pk, user)
    #         self.assertEqual(201, response.status_code)

    #         # There should be exactly one submission for the group
    #         Submission.objects.get(submission_group=group)

    # def test_error_student_submissions_disallowed(self):
    #     self.project.allow_submissions_from_non_enrolled_students = True
    #     self.project.disallow_student_submissions = True
    #     self.project.validate_and_save()

    #     for user in (self.enrolled, self.nobody):
    #         group = SubmissionGroup.objects.validate_and_create(
    #             members=[user.username], project=self.project)
    #         response = _add_submission_request(self.files, group.pk, user)
    #         self.assertEqual(409, response.status_code)
    #         with self.assertRaises(ObjectDoesNotExist):
    #             Submission.objects.get(submission_group=group)

    def test_add_submission_student_cannot_view_project_permission_denied(self):
        self.fail()
