from django.core.files.uploadedfile import SimpleUploadedFile
from django.core.urlresolvers import reverse
from django.utils import timezone

from rest_framework import status

import autograder.core.models as ag_models
import autograder.rest_api.serializers as ag_serializers

from autograder.core.tests.temporary_filesystem_test_case import (
    TemporaryFilesystemTestCase)
import autograder.rest_api.tests.test_views.common_generic_data as test_data
import autograder.rest_api.tests.test_views.common_test_impls as test_impls


def submissions_url(group):
    return reverse('group-submissions-list', kwargs={'group_pk': group.pk})


def build_submissions(group):
    set_up_project(group.project)
    for i in range(group.members.count()):
        ag_models.Submission.objects.validate_and_create(
            _files_to_submit,
            submitter=group.member_names[i],
            submission_group=group)

    return group.submissions.all()


class ListGroupSubmissionsTestCase(test_data.Client,
                                   test_data.Project,
                                   test_data.Group,
                                   test_impls.ListObjectsTest,
                                   TemporaryFilesystemTestCase):
    def test_admin_or_staff_list_submissions(self):
        for project in self.all_projects:
            for group in self.at_least_enrolled_groups(project):
                expected_data = ag_serializers.SubmissionSerializer(
                    build_submissions(group), many=True).data
                for user in self.admin, self.staff:
                    self.do_list_objects_test(
                        self.client, user, submissions_url(group),
                        expected_data)

    def test_enrolled_list_submissions(self):
        for project in self.visible_projects:
            group = self.enrolled_group(project)
            expected_data = ag_serializers.SubmissionSerializer(
                build_submissions(group), many=True).data
            self.do_list_objects_test(
                self.client, self.enrolled, submissions_url(group),
                expected_data)

    def test_non_enrolled_list_submissions(self):
        group = self.non_enrolled_group(self.visible_public_project)
        expected_data = ag_serializers.SubmissionSerializer(
            build_submissions(group), many=True).data
        self.do_list_objects_test(
            self.client, self.nobody, submissions_url(group), expected_data)

    def test_non_group_member_list_submissions_permission_denied(self):
        group = self.enrolled_group(self.visible_public_project)
        build_submissions(group)
        non_member = self.clone_user(self.enrolled)
        for user in non_member, self.nobody:
            self.do_permission_denied_get_test(
                self.client, user, submissions_url(group))

    def test_enrolled_list_submissions_project_hidden_permission_denied(self):
        for project in self.hidden_projects:
            group = self.enrolled_group(project)
            build_submissions(group)
            self.do_permission_denied_get_test(
                self.client, self.enrolled, submissions_url(group))

    def test_non_enrolled_list_submissions_project_hidden_permission_denied(self):
        group = self.non_enrolled_group(self.hidden_public_project)
        build_submissions(group)
        self.do_permission_denied_get_test(
            self.client, self.nobody, submissions_url(group))

    def test_non_enrolled_list_submissions_project_private_permission_denied(self):
        group = self.non_enrolled_group(self.visible_public_project)
        build_submissions(group)
        self.visible_public_project.validate_and_update(
            allow_submissions_from_non_enrolled_students=False)
        self.do_permission_denied_get_test(
            self.client, self.nobody, submissions_url(group))


class CreateSubmissionTestCase(test_data.Client,
                               test_data.Project,
                               test_data.Group,
                               test_impls.CreateObjectTest,
                               TemporaryFilesystemTestCase):
    def test_admin_or_staff_submit(self):
        self.fail()

    def test_enrolled_submit(self):
        self.fail()

    def test_non_enrolled_submit(self):
        self.fail()

    def test_submit_missing_and_discarded_files_tracked(self):
        self.fail()

    def test_non_group_member_submit_permission_denied(self):
        self.fail()

    def test_enrolled_submit_hidden_project_permission_denied(self):
        self.fail()

    def test_non_enrolled_submit_hidden_project_permission_denied(self):
        self.fail()

    def test_non_enrolled_submit_private_project_permission_denied(self):
        self.fail()

    def test_non_staff_submit_deadline_past(self):
        self.fail()

    def test_non_staff_submit_deadline_past_but_has_extension(self):
        self.fail()

    def test_non_staff_submit_deadline_and_extension_past(self):
        self.fail()


def set_up_project(project):
    if project.expected_student_file_patterns.count():
        return

    ag_models.ExpectedStudentFilePattern.objects.validate_and_create(
        pattern='spam.cpp', project=project)
    ag_models.ExpectedStudentFilePattern.objects.validate_and_create(
        pattern='*.txt', project=project, max_num_matches=3)


_files_to_submit = [
    SimpleUploadedFile('spam.cpp', b'steve'),
    SimpleUploadedFile('egg.txt', b'stave'),
    SimpleUploadedFile('sausage.txt', b'stove')
]
