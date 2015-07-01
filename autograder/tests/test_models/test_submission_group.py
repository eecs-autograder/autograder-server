import datetime

from django.utils import timezone

from django.contrib.auth.models import User

from autograder.tests.temporary_filesystem_test_case import (
    TemporaryFilesystemTestCase)

from autograder.models import (
    Project, Semester, Course, SubmissionGroup)


def _make_dummy_user(username, password):
    user = User.objects.create(username=username)
    user.set_password(password)
    return user


class SubmissionGroupTestCase(TemporaryFilesystemTestCase):
    def setUp(self):
        super().setUp()

        self.course = Course.objects.create(name='eecs280')
        self.semester = Semester.objects.create(name='f15', course=self.course)

        self.project = Project.objects.create(
            name='my_project', semester=self.semester, max_group_size=2)

        self.group_members = [
            _make_dummy_user('steve', 'spam'),
            _make_dummy_user('joe', 'eggs')
        ]

    # -------------------------------------------------------------------------

    def test_valid_initialization_with_defaults(self):
        group = SubmissionGroup.objects.create_group(
            self.group_members, project=self.project)

        loaded_group = SubmissionGroup.objects.get(
            pk=group.pk)

        self.assertEqual(group, loaded_group)
        self.assertIsNone(loaded_group.extended_due_date)
        self.assertEqual(self.group_members, list(loaded_group.members.all()))
        self.assertEqual(self.project, loaded_group.project)

    # -------------------------------------------------------------------------

    def test_valid_initialization_no_defaults(self):
        extended_due_date = timezone.now() + datetime.timedelta(days=1)
        group = SubmissionGroup.objects.create_group(
            self.group_members, project=self.project,
            extended_due_date=extended_due_date)

        loaded_group = SubmissionGroup.objects.get(
            pk=group.pk)

        self.assertEqual(group, loaded_group)
        self.assertEqual(loaded_group.extended_due_date, extended_due_date)
        self.assertEqual(self.group_members, list(loaded_group.members.all()))
        self.assertEqual(self.project, loaded_group.project)

    # -------------------------------------------------------------------------

    def test_valid_member_of_multiple_groups_for_different_projects(self):
        other_project = Project.objects.create(
            name='project spam', semester=self.semester, max_group_size=2)

        repeated_user = self.group_members[0]

        first_group = SubmissionGroup.objects.create_group(
            self.group_members, project=self.project)

        second_group = SubmissionGroup.objects.create_group(
            [repeated_user], project=other_project)

        loaded_first_group = SubmissionGroup.objects.get(pk=first_group.pk)
        self.assertEqual(first_group, loaded_first_group)
        self.assertEqual(
            self.group_members, list(loaded_first_group.members.all()))
        self.assertEqual(self.project, loaded_first_group.project)

        loaded_second_group = SubmissionGroup.objects.get(pk=second_group)
        self.assertEqual(second_group, loaded_second_group)
        self.assertEqual(
            [repeated_user], list(loaded_second_group.members.all()))
        self.assertEqual(other_project, loaded_second_group.project)

        self.assertEqual(
            [first_group, second_group],
            list(repeated_user.submission_groups.all()))

    # -------------------------------------------------------------------------

    def test_exception_on_too_few_group_members(self):
        with self.assertRaises(ValueError):
            SubmissionGroup.objects.create_group([], project=self.project)

        self.assertEqual([], list(SubmissionGroup.objects.all()))

    # -------------------------------------------------------------------------

    def test_exception_on_too_many_group_members(self):
        self.project.save()

        self.group_members.append(_make_dummy_user('fred', 'sausage'))
        with self.assertRaises(ValueError):
            SubmissionGroup.objects.create_group(
                self.group_members, project=self.project)

        self.assertEqual([], list(SubmissionGroup.objects.all()))

    # -------------------------------------------------------------------------

    def test_exception_on_group_member_already_in_another_group(self):
        group = SubmissionGroup.objects.create_group(
            self.group_members[0:1], project=self.project)

        with self.assertRaises(ValueError):
            SubmissionGroup.objects.create_group(
                self.group_members, project=self.project)

        self.assertEqual([group], list(SubmissionGroup.objects.all()))
