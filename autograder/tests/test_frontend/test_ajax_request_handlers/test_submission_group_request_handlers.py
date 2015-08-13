import datetime

from django.core.exceptions import ObjectDoesNotExist
from django.utils import timezone

from autograder.tests.temporary_filesystem_test_case import (
    TemporaryFilesystemTestCase)

import autograder.tests.dummy_object_utils as obj_ut

from .utils import (
    process_get_request, process_post_request,
    process_patch_request, json_load_bytes, RequestHandlerTestCase)

from autograder.frontend.json_api_serializers import (
    project_to_json, submission_group_to_json)
from autograder.models import SubmissionGroup


def _names(users):
    return [user.username for user in users]


class _SetUpBase(RequestHandlerTestCase):
    def setUp(self):
        super().setUp()

        self.admin = obj_ut.create_dummy_users()
        self.staff = obj_ut.create_dummy_users()
        self.enrolled = obj_ut.create_dummy_users()
        self.nobody = obj_ut.create_dummy_users()

        self.course = obj_ut.create_dummy_courses()
        self.semester = obj_ut.create_dummy_semesters(self.course)

        self.course.add_course_admins(self.admin)
        self.semester.add_semester_staff(self.staff)
        self.semester.add_enrolled_students(self.enrolled)

        self.project = obj_ut.create_dummy_projects(self.semester)
        self.project.max_group_size = 3
        self.project.save()


class CreateSubmissionGroupRequestTestCase(_SetUpBase):
    def setUp(self):
        super().setUp()

        self.group_json_starter = {
            'data': {
                'type': 'submission_group',
                'attributes': {
                    'members': [],
                },
                'relationships': {
                    'project': {
                        'data': project_to_json(self.project)
                    }
                }
            }
        }

    def test_valid_create_user_in_group(self):
        members = [self.enrolled] + obj_ut.create_dummy_users(2)
        self.semester.add_enrolled_students(*members)
        self.group_json_starter['data']['attributes']['members'] = [
            member.username for member in members]

        response = _add_submission_group_request(
            self.group_json_starter, self.enrolled)
        self.assertEqual(201, response.status_code)

        response_content = json_load_bytes(response.content)
        id_ = response_content['data']['id']
        loaded = SubmissionGroup.objects.get(pk=id_)
        expected = {
            'data': submission_group_to_json(loaded)
            # TODO: include submissions
        }
        self.assertJSONObjsEqual(expected, response_content)

    def test_valid_admin_create_other_group(self):
        members = obj_ut.create_dummy_users(2)
        self.semester.add_enrolled_students(*members)
        self.group_json_starter['data']['attributes']['members'] = [
            member.username for member in members]

        response = _add_submission_group_request(
            self.group_json_starter, self.admin)
        self.assertEqual(201, response.status_code)

        response_content = json_load_bytes(response.content)
        id_ = response_content['data']['id']
        loaded = SubmissionGroup.objects.get(pk=id_)
        expected = {
            'data': submission_group_to_json(loaded)
        }
        self.assertJSONObjsEqual(expected, response_content)

    def test_error_user_already_in_group(self):
        new_users = obj_ut.create_dummy_users(2)
        self.semester.add_enrolled_students(*new_users)
        members = [self.enrolled] + new_users
        self.group_json_starter['data']['attributes']['members'] = _names(
            members)

        SubmissionGroup.objects.validate_and_create(
            members=_names(members), project=self.project)

        creator = members[-1]
        self.group_json_starter['data']['attributes']['members'] = [
            creator.username]

        response = _add_submission_group_request(
            self.group_json_starter, creator)
        self.assertEqual(409, response.status_code)

    def test_error_project_not_found(self):
        self.group_json_starter['data']['relationships'][
            'project']['data']['id'] = 42
        response = _add_submission_group_request(
            self.group_json_starter, self.enrolled)
        self.assertEqual(404, response.status_code)

    def test_error_group_too_large(self):
        members = [self.enrolled] + obj_ut.create_dummy_users(3)
        self.group_json_starter['data']['attributes']['members'] = [
            member.username for member in members]

        response = _add_submission_group_request(
            self.group_json_starter, self.enrolled)
        self.assertEqual(409, response.status_code)

    def test_error_group_too_small(self):
        response = _add_submission_group_request(
            self.group_json_starter, self.enrolled)
        self.assertEqual(409, response.status_code)

    def test_permission_denied(self):
        bad_create_pairings = (
            # Creating user not in members list
            (self.enrolled, obj_ut.create_dummy_users(2)),
            (self.nobody, obj_ut.create_dummy_users(2)),
            # Non-admin staff can't create other groups
            (self.staff, obj_ut.create_dummy_users(2))
        )

        for creator, members in bad_create_pairings:
            self.group_json_starter['data']['attributes']['members'] = [
                member.username for member in members]

            response = _add_submission_group_request(
                self.group_json_starter, creator)

            self.assertEqual(403, response.status_code)


def _add_submission_group_request(data, user):
    url = '/submission-groups/submission-group/'
    return process_post_request(url, data, user)

# -----------------------------------------------------------------------------


class GetSubmissionGroupRequestTestCase(_SetUpBase):
    def setUp(self):
        super().setUp()

        new_users = obj_ut.create_dummy_users(2)
        self.semester.add_enrolled_students(*new_users)
        self.members = [self.enrolled] + new_users
        self.group = SubmissionGroup.objects.validate_and_create(
            members=_names(self.members), project=self.project)

    def test_valid_get_own_group(self):
        response = _get_submission_group_request(
            self.project.pk, self.enrolled.username, self.enrolled)
        self.assertEqual(200, response.status_code)

        expected = {
            'data': submission_group_to_json(self.group)
            # TODO: include submissions
        }

        self.assertJSONObjsEqual(expected, json_load_bytes(response.content))

        response = _get_submission_group_by_id_request(
            self.group.pk, self.enrolled)
        self.assertEqual(200, response.status_code)

        self.assertJSONObjsEqual(expected, json_load_bytes(response.content))

    def test_valid_admin_or_staff_get_other_group(self):
        expected = {
            'data': submission_group_to_json(self.group)
            # TODO: include submissions
        }

        for user in (self.admin, self.staff):
            response = _get_submission_group_request(
                self.project.pk, self.enrolled.username, user)
            self.assertEqual(200, response.status_code)

            self.assertJSONObjsEqual(
                expected, json_load_bytes(response.content))

            response = _get_submission_group_by_id_request(self.group.pk, user)
            self.assertEqual(200, response.status_code)

            self.assertJSONObjsEqual(
                expected, json_load_bytes(response.content))

    def test_error_group_not_found(self):
        response = _get_submission_group_request(
            self.project.pk, 'steve_the_nonexistant_user', self.admin)
        self.assertEqual(404, response.status_code)

        response = _get_submission_group_request(
            self.project.pk, self.nobody.username, self.nobody)
        self.assertEqual(404, response.status_code)

        response = _get_submission_group_by_id_request(42, self.admin)
        self.assertEqual(404, response.status_code)

    def test_error_project_not_found(self):
        response = _get_submission_group_request(
            42, self.enrolled.username, self.enrolled)
        self.assertEqual(404, response.status_code)

    def test_permission_denied(self):
        other_enrolled = obj_ut.create_dummy_users()

        for user in (other_enrolled, self.nobody):
            response = _get_submission_group_request(
                self.project.pk, self.enrolled.username, user)
            self.assertEqual(403, response.status_code)

            response = _get_submission_group_by_id_request(
                self.group.pk, user)
            self.assertEqual(403, response.status_code)


def _get_submission_group_request(project_id, username, requesting_user):
    url = '/submission-groups/submission-group/?project_id={}&username={}'.format(
        project_id, username)
    return process_get_request(url, requesting_user)


def _get_submission_group_by_id_request(group_id, requesting_user):
    url = '/submission-groups/submission-group/{}/'.format(group_id)
    return process_get_request(url, requesting_user)


# -----------------------------------------------------------------------------

class PatchSubmissionGroupRequestTestCase(_SetUpBase):
    def setUp(self):
        super().setUp()

        new_users = obj_ut.create_dummy_users(2)
        self.semester.add_enrolled_students(*new_users)
        self.members = [self.enrolled] + new_users
        self.group = SubmissionGroup.objects.validate_and_create(
            members=_names(self.members), project=self.project)

        self.extended_due_date = (
            timezone.now() + datetime.timedelta(days=1)).replace(
            microsecond=0)
        self.patch_data = {
            'data': {
                'type': 'submission_group',
                'id': self.group.pk,
                'attributes': {
                    'extended_due_date': self.extended_due_date
                }
            }
        }

    def test_valid_update_extended_due_date(self):
        # Grant extension
        response = _patch_submission_group_request(
            self.group.pk, self.patch_data, self.admin)
        self.assertEqual(204, response.status_code)

        loaded = SubmissionGroup.objects.get(pk=self.group.pk)

        self.assertJSONObjsEqual(
            loaded.extended_due_date, self.extended_due_date)

        # Remove extension
        self.patch_data['data']['attributes']['extended_due_date'] = None
        response = _patch_submission_group_request(
            self.group.pk, self.patch_data, self.admin)
        self.assertEqual(204, response.status_code)

        loaded = SubmissionGroup.objects.get(pk=self.group.pk)

        self.assertJSONObjsEqual(loaded.extended_due_date, None)

    # def test_error_trying_to_edit_non_editable_fields(self):
    #     self.fail()

    def test_error_group_not_found(self):
        self.patch_data['data']['id'] = 42

        response = _patch_submission_group_request(
            42, self.patch_data, self.admin)
        self.assertEqual(404, response.status_code)

    def test_permission_denied(self):
        for user in (self.enrolled, self.nobody, self.staff):
            response = _patch_submission_group_request(
                self.group.pk, self.patch_data, user)
            self.assertEqual(403, response.status_code)

            loaded = SubmissionGroup.objects.get(pk=self.group.pk)

            self.assertEqual(loaded.extended_due_date, None)


def _patch_submission_group_request(group_id, data, user):
    url = '/submission-groups/submission-group/{}/'.format(group_id)
    return process_patch_request(url, data, user)


# -----------------------------------------------------------------------------

# class DeleteSubmissionGroupRequestTestCase(TemporaryFilesystemTestCase):
#     def test_valid_delete(self):
#         self.fail()

#     def test_error_group_not_found(self):
#         self.fail()

#     def test_permission_denied(self):
#         self.fail()
