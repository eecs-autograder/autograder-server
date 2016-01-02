import itertools
import datetime

from django.core.urlresolvers import reverse
from django.utils import timezone, dateparse
from django.core.exceptions import ObjectDoesNotExist
from django.core.files.uploadedfile import SimpleUploadedFile

from autograder.core.models import SubmissionGroup, Submission
from autograder.core.tests.temporary_filesystem_test_case import (
    TemporaryFilesystemTestCase)
import autograder.core.tests.dummy_object_utils as obj_ut
from .utilities import MockClient, json_load_bytes, sorted_by_pk
from autograder.rest_api import url_shortcuts


def _common_setup(fixture):
    fixture.admin = obj_ut.create_dummy_user()
    fixture.staff = obj_ut.create_dummy_user()
    fixture.enrolled = obj_ut.create_dummy_user()
    fixture.nobody = obj_ut.create_dummy_user()

    fixture.hidden_project = obj_ut.build_project(
        course_kwargs={'administrators': [fixture.admin]},
        semester_kwargs={
            'staff': [fixture.staff], 'enrolled_students': [fixture.enrolled]},
        project_kwargs={'allow_submissions_from_non_enrolled_students': True})

    fixture.semester = fixture.hidden_project.semester
    fixture.course = fixture.semester.course

    fixture.admin.courses_is_admin_for.add(fixture.course)
    fixture.staff.semesters_is_staff_for.add(fixture.semester)
    fixture.enrolled.semesters_is_enrolled_in.add(fixture.semester)

    fixture.visible_project = obj_ut.build_project(
        project_kwargs={'semester': fixture.semester,
                        'visible_to_students': True,
                        'allow_submissions_from_non_enrolled_students': True})

    fixture.course_url = reverse(
        'course:get', kwargs={'pk': fixture.course.pk})

    fixture.semester_url = reverse(
        'semester:get', kwargs={'pk': fixture.semester.pk})
    fixture.staff_url = reverse(
        'semester:staff', kwargs={'pk': fixture.semester.pk})
    fixture.enrolled_url = reverse(
        'semester:enrolled_students', kwargs={'pk': fixture.semester.pk})
    fixture.projects_url = reverse(
        'semester:projects', kwargs={'pk': fixture.semester.pk})

    fixture.hidden_project_url = reverse(
        'project:get', kwargs={'pk': fixture.hidden_project.pk})
    fixture.visible_project_url = reverse(
        'project:get', kwargs={'pk': fixture.visible_project.pk})

    fixture.admin_group_obj = _make_group_obj(
        fixture.admin, fixture.visible_project)
    fixture.staff_group_obj = _make_group_obj(
        fixture.staff, fixture.visible_project)
    fixture.enrolled_group_obj = _make_group_obj(
        fixture.enrolled, fixture.visible_project)
    fixture.nobody_group_obj = _make_group_obj(
        fixture.nobody, fixture.visible_project)

    fixture.users_and_groups_visible_proj = [
        fixture.admin_group_obj, fixture.staff_group_obj,
        fixture.enrolled_group_obj, fixture.nobody_group_obj
    ]

    fixture.users_and_groups_hidden_proj = [
        _make_group_obj(user, fixture.hidden_project)
        for user in (fixture.admin, fixture.staff,
                     fixture.enrolled, fixture.nobody)
    ]


def _make_group_obj(user, project):
    obj = {
        'user': user,
        'group': SubmissionGroup.objects.validate_and_create(
            members=[user.username], project=project),
    }
    obj['url'] = reverse('group:get', kwargs={'pk': obj['group'].pk})
    return obj


class GetUpdateDeleteSubmissionGroupTestCase(TemporaryFilesystemTestCase):
    def setUp(self):
        super().setUp()

        _common_setup(self)

    def test_user_get_own_group(self):
        for obj in self.users_and_groups_visible_proj:
            client = MockClient(obj['user'])
            response = client.get(obj['url'])
            self.assertEqual(200, response.status_code)

            expected_content = {
                "type": "submission_group",
                "id": obj['group'].pk,
                "members": list(obj['group'].member_names),
                "extended_due_date": None,
                "urls": {
                    "self": obj['url'],
                    "project": self.visible_project_url,
                    "submissions": reverse('group:submissions',
                                           kwargs={'pk': obj['group'].pk})
                }
            }

            self.assertEqual(
                expected_content, json_load_bytes(response.content))

    def test_course_admin_or_semester_staff_get_student_group(self):
        student_objs = [
            obj for obj in
            itertools.chain(
                self.users_and_groups_visible_proj,
                self.users_and_groups_hidden_proj)
            if obj['user'] in (self.enrolled, self.nobody)
        ]
        for user in self.admin, self.staff:
            client = MockClient(user)
            for group_obj in student_objs:
                response = client.get(group_obj['url'])
                self.assertEqual(200, response.status_code)

                expected_content = {
                    "type": "submission_group",
                    "id": group_obj['group'].pk,
                    "members": list(group_obj['group'].member_names),
                    "extended_due_date": None,
                    "urls": {
                        "self": group_obj['url'],
                        "project": url_shortcuts.project_url(
                            group_obj['group'].project),
                        "submissions": reverse(
                            'group:submissions',
                            kwargs={'pk': group_obj['group'].pk})
                    }
                }

                self.assertEqual(
                    expected_content, json_load_bytes(response.content))

    def test_student_get_other_group_permission_denied(self):
        for user in self.enrolled, self.nobody:
            client = MockClient(user)
            for group_obj in self.users_and_groups_visible_proj:
                if group_obj['user'] == user:
                    continue
                response = client.get(group_obj['url'])
                self.assertEqual(403, response.status_code)

    def test_get_submission_group_user_cannot_view_project_permission_denied(self):
        for user in self.enrolled, self.nobody:
            client = MockClient(user)
            for group_obj in self.users_and_groups_hidden_proj:
                if group_obj['user'] != user:
                    continue

                response = client.get(group_obj['url'])
                self.assertEqual(403, response.status_code)

    # -------------------------------------------------------------------------

    def test_course_admin_edit_group(self):
        new_member = obj_ut.create_dummy_user()
        new_member.semesters_is_enrolled_in.add(self.semester)

        new_members = list(sorted(
            [self.enrolled.username, new_member.username]))

        client = MockClient(self.admin)
        response = client.patch(
            self.enrolled_group_obj['url'],
            {'members': new_members})
        self.assertEqual(200, response.status_code)

        loaded = SubmissionGroup.get_group(self.enrolled, self.visible_project)
        self.assertCountEqual(
            [new_member.username, self.enrolled.username], loaded.member_names)

        expected_content = {
            'members': new_members
        }

        actual_content = json_load_bytes(response.content)
        actual_content['members'].sort()

        self.assertEqual(expected_content, actual_content)

        new_due_date = timezone.now().replace(microsecond=0)
        response = client.patch(
            self.enrolled_group_obj['url'],
            {'members': [new_member.username],
             'extended_due_date': new_due_date})

        self.assertEqual(200, response.status_code)

        expected_content = {
            'members': [new_member.username],
            'extended_due_date': new_due_date
        }

        actual_content = json_load_bytes(response.content)
        actual_content['extended_due_date'] = dateparse.parse_datetime(
            actual_content['extended_due_date'])
        self.assertEqual(expected_content, actual_content)

    def test_other_edit_group_permission_denied(self):
        for user in self.enrolled, self.nobody, self.staff:
            client = MockClient(user)
            for group_obj in self.users_and_groups_visible_proj:
                response = client.patch(
                    group_obj['url'], {'extended_due_date': timezone.now()})
                self.assertEqual(403, response.status_code)

                loaded = SubmissionGroup.objects.get(pk=group_obj['group'].pk)
                self.assertIsNone(loaded.extended_due_date)

    # -------------------------------------------------------------------------

    def test_course_admin_delete_group(self):
        client = MockClient(self.admin)
        response = client.delete(self.enrolled_group_obj['url'])
        self.assertEqual(204, response.status_code)

        with self.assertRaises(ObjectDoesNotExist):
            SubmissionGroup.objects.get(pk=self.enrolled_group_obj['group'].pk)

    def test_other_delete_group_permission_denied(self):
        for user in self.staff, self.enrolled, self.nobody:
            client = MockClient(user)
            response = client.delete(self.enrolled_group_obj['url'])
            self.assertEqual(403, response.status_code)

            SubmissionGroup.objects.get(pk=self.enrolled_group_obj['group'].pk)

# -----------------------------------------------------------------------------
# -----------------------------------------------------------------------------


class ListSubmissionTestCase(TemporaryFilesystemTestCase):
    def setUp(self):
        super().setUp()

        _common_setup(self)

        for obj in self.users_and_groups_visible_proj:
            obj['submissions_url'] = reverse(
                'group:submissions', kwargs={'pk': obj['group'].pk})

            obj['submissions'] = []
            for i in range(2):
                new_submission = Submission(
                    submission_group=obj['group'],
                    status=Submission.GradingStatus.finished_grading)
                new_submission.save()
                obj['submissions'].append(new_submission)

    def test_user_list_own_submissions(self):
        for obj in self.users_and_groups_visible_proj:
            client = MockClient(obj['user'])
            response = client.get(obj['submissions_url'])
            self.assertEqual(200, response.status_code)

            expected_content = {
                'submissions': [
                    {
                        'timestamp': str(sub.timestamp),
                        'url': reverse('submission:get', kwargs={'pk': sub.pk})
                    }
                    for sub in obj['submissions']
                ]
            }

            self.assertEqual(
                expected_content, json_load_bytes(response.content))

    def test_course_admin_or_semester_staff_list_student_submissions(self):
        for user in self.staff, self.admin:
            client = MockClient(user)
            for obj in self.enrolled_group_obj, self.nobody_group_obj:
                response = client.get(obj['submissions_url'])
                self.assertEqual(200, response.status_code)

                expected_content = {
                    'submissions': [
                        {
                            'timestamp': str(sub.timestamp),
                            'url': reverse(
                                'submission:get', kwargs={'pk': sub.pk})
                        }
                        for sub in obj['submissions']
                    ]
                }

                self.assertEqual(
                    expected_content, json_load_bytes(response.content))

    def test_non_admin_non_staff_list_other_submissions_permission_denied(self):
        for user in self.enrolled, self.nobody:
            client = MockClient(user)
            for obj in self.users_and_groups_visible_proj:
                if obj['user'] == user:
                    continue
                response = client.get(obj['submissions_url'])
                self.assertEqual(403, response.status_code)

    def test_list_submissions_student_cannot_view_project_permission_denied(self):
        for user in self.enrolled, self.nobody:
            client = MockClient(user)
            for obj in self.users_and_groups_hidden_proj:
                url = reverse(
                    'group:submissions', kwargs={'pk': obj['group'].pk})
                response = client.get(url)
                self.assertEqual(403, response.status_code)

# -----------------------------------------------------------------------------


class AddSubmissionTestCase(TemporaryFilesystemTestCase):
    def setUp(self):
        super().setUp()

        _common_setup(self)

        self.visible_project.required_student_files = ['spam.txt']
        self.visible_project.validate_and_save()

        self.files_to_submit = [
            SimpleUploadedFile('spam.txt', b'asdfadsf')
        ]

        for obj in itertools.chain(self.users_and_groups_visible_proj,
                                   self.users_and_groups_hidden_proj):
            obj['submissions_url'] = reverse(
                'group:submissions', kwargs={'pk': obj['group'].pk})

    def test_valid_submit(self):
        for obj in self.users_and_groups_visible_proj:
            client = MockClient(obj['user'])
            response = client.post(
                obj['submissions_url'], {'files': self.files_to_submit},
                encode_data=False)

            self.assertEqual(201, response.status_code)

            self.assertEqual(1, obj['group'].submissions.count())
            loaded = obj['group'].submissions.all().first()

            expected_content = {
                'timestamp': str(loaded.timestamp),
                'url': reverse('submission:get', kwarge={'pk': loaded.pk})
            }

            self.assertEqual(
                expected_content, json_load_bytes(response.content))

    def test_permission_denied_user_not_in_specified_group(self):
        new_user = obj_ut.create_dummy_user()
        self.semester.add_enrolled_students(new_user)

        client = MockClient(new_user)
        response = client.post(
            self.enrolled_group_obj['submissions_url'],
            {'files': self.files_to_submit},
            encode_data=False)

        self.assertEqual(403, response.status_code)

        self.assertEqual(
            0, self.enrolled_group_obj['group'].submissions.count())

    def test_invalid_already_has_submit_in_queue(self):
        for obj in self.users_and_groups_visible_proj:
            client = MockClient(obj['user'])
            response = client.post(
                obj['submissions_url'], {'files': self.files_to_submit},
                encode_data=False)
            self.assertEqual(201, response.status_code)

            response = client.post(
                obj['submissions_url'], {'files': self.files_to_submit},
                encode_data=False)
            self.assertEqual(403, response.status_code)

            # Throws an exception if more than 1 submission
            # exists for the group
            self.assertEqual(1, obj['group'].submissions.count())

    def test_error_project_deadline_passed(self):
        self.visible_project.closing_time = (
            timezone.now() + datetime.timedelta(minutes=-1))
        self.visible_project.validate_and_save()

        for obj in (self.enrolled_group_obj, self.nobody_group_obj):
            client = MockClient(obj['user'])
            response = client.post(
                obj['submissions_url'], {'files': self.files_to_submit},
                encode_data=False)
            self.assertEqual(403, response.status_code)
            with self.assertRaises(ObjectDoesNotExist):
                Submission.objects.get(submission_group=obj['group'])

    def test_no_error_project_deadline_passed_but_group_has_extension(self):
        self.visible_project.closing_time = (
            timezone.now() + datetime.timedelta(minutes=-1))
        self.visible_project.validate_and_save()

        extension = (
            self.visible_project.closing_time + datetime.timedelta(days=1))
        for obj in (self.enrolled_group_obj, self.nobody_group_obj):
            client = MockClient(obj['user'])
            obj['group'].extended_due_date = extension
            obj['group'].save()
            response = client.post(
                obj['submissions_url'], {'files': self.files_to_submit},
                encode_data=False)
            self.assertEqual(201, response.status_code)

            self.assertEqual(1, obj['group'].submissions.count())

    def test_error_project_deadline_and_extension_passed(self):
        self.visible_project.closing_time = (
            timezone.now() + datetime.timedelta(days=-1))
        self.visible_project.validate_and_save()

        extension = timezone.now() + datetime.timedelta(minutes=-1)
        for obj in (self.enrolled_group_obj, self.nobody_group_obj):
            client = MockClient(obj['user'])
            obj['group'].extended_due_date = extension
            obj['group'].save()
            response = client.post(
                obj['submissions_url'], {'files': self.files_to_submit},
                encode_data=False)
            self.assertEqual(403, response.status_code)
            with self.assertRaises(ObjectDoesNotExist):
                Submission.objects.get(submission_group=obj['group'])

    def test_no_error_admin_or_staff_submit_passed_deadline(self):
        self.visible_project.closing_time = (
            timezone.now() + datetime.timedelta(minutes=-1))
        self.visible_project.validate_and_save()

        for obj in (self.admin_group_obj, self.staff_group_obj):
            client = MockClient(obj['user'])
            response = client.post(
                obj['submissions_url'], {'files': self.files_to_submit},
                encode_data=False)
            self.assertEqual(201, response.status_code)

            self.assertEqual(1, obj['group'].submissions.count())

    def test_error_student_submissions_disallowed(self):
        self.visible_project.disallow_student_submissions = True
        self.visible_project.validate_and_save()

        for obj in (self.enrolled_group_obj, self.nobody_group_obj):
            client = MockClient(obj['user'])
            response = client.post(
                obj['submissions_url'], {'files': self.files_to_submit},
                encode_data=False)
            self.assertEqual(403, response.status_code)
            with self.assertRaises(ObjectDoesNotExist):
                Submission.objects.get(submission_group=obj['group'])

    def test_student_add_submission_project_hidden_permission_denied(self):
        for user in self.enrolled, self.nobody:
            client = MockClient(user)
            for obj in self.users_and_groups_hidden_proj:
                if obj['user'] != user:
                    continue

                response = client.post(
                    obj['submissions_url'], {'files': self.files_to_submit},
                    encode_data=False)
                self.assertEqual(403, response.status_code)

                self.assertEqual(0, obj['group'].submissions.count())

    def test_non_enrolled_student_non_public_project_permission_denied(self):
        self.visible_project.allow_submissions_from_non_enrolled_students = False
        self.visible_project.validate_and_save()
        client = MockClient(self.nobody)
        response = client.post(
            self.nobody_group_obj['submissions_url'],
            {'files': self.files_to_submit},
            encode_data=False)
        self.assertEqual(403, response.status_code)

        self.assertEqual(0, self.nobody_group_obj['group'].submissions.count())
