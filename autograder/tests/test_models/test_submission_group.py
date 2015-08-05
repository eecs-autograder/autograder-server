import os
import datetime

from django.utils import timezone
from django.core.exceptions import ValidationError

from autograder.tests.temporary_filesystem_test_case import (
    TemporaryFilesystemTestCase)

from autograder.models import (
    Project, Semester, Course, SubmissionGroup)

import autograder.shared.utilities as ut
import autograder.tests.dummy_object_utils as obj_ut


class SubmissionGroupTestCase(TemporaryFilesystemTestCase):
    def setUp(self):
        super().setUp()

        self.course = Course.objects.create(name='eecs280')
        self.semester = Semester.objects.create(name='f15', course=self.course)

        self.project = Project.objects.create(
            name='my_project', semester=self.semester, max_group_size=2)

        self.enrolled_group = obj_ut.create_dummy_users(2)
        self.semester.add_enrolled_students(*self.enrolled_group)

        self.staff_group = obj_ut.create_dummy_users(2)
        self.semester.add_semester_staff(*self.staff_group)

        self.non_enrolled_group = obj_ut.create_dummy_users(2)

        self.user_sort_key = lambda user: user.username

    def assertListsEqual(self, first_list, second_list, sort_key=None):
        self.assertEqual(
            sorted(first_list, key=sort_key),
            sorted(second_list, key=sort_key))

    # -------------------------------------------------------------------------

    def test_valid_initialization_with_defaults(self):
        group = SubmissionGroup.objects.create_group(
            self.enrolled_group, project=self.project)

        loaded_group = SubmissionGroup.objects.get(
            pk=group.pk)

        self.assertEqual(group, loaded_group)
        self.assertIsNone(loaded_group.extended_due_date)
        self.assertListsEqual(
            self.enrolled_group, list(loaded_group.members.all()),
            self.user_sort_key)
        self.assertEqual(self.project, loaded_group.project)

        self.assertTrue(
            os.path.isdir(ut.get_student_submission_group_dir(loaded_group)))

    def test_valid_initialization_no_defaults(self):
        extended_due_date = timezone.now() + datetime.timedelta(days=1)
        group = SubmissionGroup.objects.create_group(
            self.enrolled_group, project=self.project,
            extended_due_date=extended_due_date)

        loaded_group = SubmissionGroup.objects.get(
            pk=group.pk)

        self.assertEqual(group, loaded_group)
        self.assertEqual(loaded_group.extended_due_date, extended_due_date)
        self.assertListsEqual(
            self.enrolled_group, list(loaded_group.members.all()),
            self.user_sort_key)
        self.assertEqual(self.project, loaded_group.project)

    def test_valid_member_of_multiple_groups_for_different_projects(self):
        other_project = Project.objects.create(
            name='project spam', semester=self.semester, max_group_size=2)

        repeated_user = self.enrolled_group[0]

        first_group = SubmissionGroup.objects.create_group(
            self.enrolled_group, project=self.project)

        second_group = SubmissionGroup.objects.create_group(
            [repeated_user], project=other_project)

        loaded_first_group = SubmissionGroup.objects.get(pk=first_group.pk)
        self.assertEqual(first_group, loaded_first_group)
        self.assertListsEqual(
            self.enrolled_group, list(loaded_first_group.members.all()),
            self.user_sort_key)
        self.assertEqual(self.project, loaded_first_group.project)

        loaded_second_group = SubmissionGroup.objects.get(pk=second_group)
        self.assertEqual(second_group, loaded_second_group)
        self.assertEqual(
            [repeated_user], list(loaded_second_group.members.all()))
        self.assertEqual(other_project, loaded_second_group.project)

        self.assertListsEqual(
            [first_group, second_group],
            list(repeated_user.submission_groups.all()),
            lambda obj: obj.pk)

    def test_exception_on_normal_create_method(self):
        with self.assertRaises(NotImplementedError):
            SubmissionGroup.objects.create(project=self.project)

    def test_exception_on_too_few_group_members(self):
        with self.assertRaises(ValidationError):
            SubmissionGroup.objects.create_group([], project=self.project)

        self.assertEqual([], list(SubmissionGroup.objects.all()))

    def test_exception_on_too_many_group_members(self):
        self.project.save()

        new_user = obj_ut.create_dummy_users()
        self.semester.add_enrolled_students(new_user)
        self.enrolled_group.append(new_user)

        with self.assertRaises(ValidationError):
            SubmissionGroup.objects.create_group(
                self.enrolled_group, project=self.project)

        self.assertEqual([], list(SubmissionGroup.objects.all()))

    def test_exception_on_group_member_already_in_another_group(self):
        group = SubmissionGroup.objects.create_group(
            self.enrolled_group[0:1], project=self.project)

        with self.assertRaises(ValidationError):
            SubmissionGroup.objects.create_group(
                self.enrolled_group, project=self.project)

        self.assertEqual([group], list(SubmissionGroup.objects.all()))

    def test_exception_on_some_members_not_enrolled(self):
        mixed_group = self.enrolled_group[0:1] + [obj_ut.create_dummy_users()]
        with self.assertRaises(ValidationError):
            SubmissionGroup.objects.create_group(
                mixed_group, project=self.project)

        self.project.allow_submissions_from_non_enrolled_students = True
        self.project.save()

        with self.assertRaises(ValidationError):
            SubmissionGroup.objects.create_group(
                mixed_group, project=self.project)

    def test_no_exception_group_of_staff_members(self):
        group = SubmissionGroup.objects.create_group(
            self.staff_group, project=self.project)

        loaded_group = SubmissionGroup.objects.get(pk=group)

        self.assertEqual(group, loaded_group)
        self.assertListsEqual(
            self.staff_group, list(loaded_group.members.all()),
            self.user_sort_key)
        self.assertEqual(self.project, loaded_group.project)

    def test_exception_all_members_not_enrolled_and_unenrolled_not_allowed(self):
        with self.assertRaises(ValidationError):
            SubmissionGroup.objects.create_group(
                self.non_enrolled_group, project=self.project)

    def test_no_exception_on_all_members_not_enrolled_and_unenrolled_allowed(self):
        self.project.allow_submissions_from_non_enrolled_students = True
        self.project.save()

        group = SubmissionGroup.objects.create_group(
            self.non_enrolled_group, project=self.project)

        loaded_group = SubmissionGroup.objects.get(pk=group)

        self.assertEqual(group, loaded_group)
        self.assertListsEqual(
            self.non_enrolled_group, list(loaded_group.members.all()),
            self.user_sort_key)
        self.assertEqual(self.project, loaded_group.project)

    def test_exception_group_mix_of_enrolled_and_staff(self):
        self.project.max_group_size = 5
        self.project.save()
        with self.assertRaises(ValidationError):
            SubmissionGroup.objects.create_group(
                self.staff_group + self.enrolled_group, project=self.project)
