import os
import datetime

from django.core.exceptions import ValidationError, ObjectDoesNotExist
# from django.db import connection, transaction
from django.utils import timezone

from autograder.core.tests.temporary_filesystem_test_case import (
    TemporaryFilesystemTestCase)

from autograder.core.models import (
    Project, Semester, Course, SubmissionGroup)

import autograder.core.shared.utilities as ut
import autograder.core.tests.dummy_object_utils as obj_ut


class SubmissionGroupTestCase(TemporaryFilesystemTestCase):
    def setUp(self):
        super().setUp()

        self.course = Course.objects.validate_and_create(name='eecs280')
        self.semester = Semester.objects.validate_and_create(
            name='f15', course=self.course)

        self.project = Project.objects.validate_and_create(
            name='my_project', semester=self.semester, max_group_size=2)

        self.enrolled_group = obj_ut.create_dummy_users(2)
        self.semester.add_enrolled_students(*self.enrolled_group)

        self.staff_group = obj_ut.create_dummy_users(2)
        self.semester.add_semester_staff(*self.staff_group)

        self.non_enrolled_group = obj_ut.create_dummy_users(2)

    # -------------------------------------------------------------------------

    def test_valid_initialization_with_defaults(self):
        group = SubmissionGroup.objects.validate_and_create(
            members=self.enrolled_group, project=self.project)

        loaded_group = SubmissionGroup.objects.get(
            pk=group.pk)

        self.assertEqual(group, loaded_group)
        self.assertIsNone(loaded_group.extended_due_date)
        self.assertCountEqual(
            self.enrolled_group, loaded_group.members.all())
        self.assertEqual(self.project, loaded_group.project)

        self.assertTrue(
            os.path.isdir(ut.get_student_submission_group_dir(loaded_group)))

    def test_valid_initialization_no_defaults(self):
        extended_due_date = timezone.now() + datetime.timedelta(days=1)
        group = SubmissionGroup.objects.validate_and_create(
            members=self.enrolled_group, project=self.project,
            extended_due_date=extended_due_date)

        loaded_group = SubmissionGroup.objects.get(pk=group.pk)

        self.assertEqual(group, loaded_group)
        self.assertEqual(loaded_group.extended_due_date, extended_due_date)
        self.assertCountEqual(
            self.enrolled_group, loaded_group.members.all())
        self.assertEqual(self.project, loaded_group.project)

    def test_valid_member_of_multiple_groups_for_different_projects(self):
        other_project = Project.objects.validate_and_create(
            name='project spam', semester=self.semester, max_group_size=2)

        repeated_user = self.enrolled_group[0]

        first_group = SubmissionGroup.objects.validate_and_create(
            members=self.enrolled_group, project=self.project)

        second_group = SubmissionGroup.objects.validate_and_create(
            members=[repeated_user], project=other_project)

        loaded_first_group = SubmissionGroup.objects.get(pk=first_group.pk)
        self.assertEqual(first_group, loaded_first_group)
        self.assertCountEqual(
            self.enrolled_group, loaded_first_group.members.all())
        self.assertEqual(self.project, loaded_first_group.project)

        loaded_second_group = SubmissionGroup.objects.get(pk=second_group.pk)
        self.assertEqual(second_group, loaded_second_group)
        self.assertCountEqual(
            [repeated_user], loaded_second_group.members.all())
        self.assertEqual(other_project, loaded_second_group.project)

        groups = list(repeated_user.groups_is_member_of.all())
        self.assertCountEqual([first_group, second_group], groups)

    def test_exception_on_normal_create_method(self):
        with self.assertRaises(NotImplementedError):
            SubmissionGroup.objects.create(project=self.project)

    def test_exception_on_too_few_group_members(self):
        with self.assertRaises(ValidationError):
            SubmissionGroup.objects.validate_and_create(
                members=[], project=self.project)

        self.assertEqual([], list(SubmissionGroup.objects.all()))

        self.project.min_group_size = 2
        self.project.validate_and_save()
        with self.assertRaises(ValidationError):
            SubmissionGroup.objects.validate_and_create(
                members=self.enrolled_group[0:1],
                project=self.project)

        self.assertEqual([], list(SubmissionGroup.objects.all()))

    def test_exception_on_too_many_group_members(self):
        self.project.save()

        new_user = obj_ut.create_dummy_user()
        self.semester.add_enrolled_students(new_user)
        self.enrolled_group.append(new_user)

        with self.assertRaises(ValidationError):
            SubmissionGroup.objects.validate_and_create(
                members=self.enrolled_group, project=self.project)

        self.assertEqual([], list(SubmissionGroup.objects.all()))

    def test_exception_on_group_member_already_in_another_group(self):
        group = SubmissionGroup.objects.validate_and_create(
            members=self.enrolled_group[0:1], project=self.project)

        with self.assertRaises(ValidationError):
            SubmissionGroup.objects.validate_and_create(
                members=self.enrolled_group, project=self.project)

        self.assertEqual([group], list(SubmissionGroup.objects.all()))

    def test_exception_on_some_members_not_enrolled(self):
        mixed_group = self.enrolled_group[0:1] + [obj_ut.create_dummy_user()]
        with self.assertRaises(ValidationError):
            SubmissionGroup.objects.validate_and_create(
                members=mixed_group, project=self.project)

        self.project.allow_submissions_from_non_enrolled_students = True
        self.project.save()

        with self.assertRaises(ValidationError):
            SubmissionGroup.objects.validate_and_create(
                members=mixed_group, project=self.project)

    def test_no_exception_group_of_staff_members(self):
        group = SubmissionGroup.objects.validate_and_create(
            members=self.staff_group, project=self.project)

        loaded_group = SubmissionGroup.objects.get(pk=group.pk)

        self.assertEqual(group, loaded_group)
        self.assertCountEqual(
            self.staff_group, loaded_group.members.all())
        self.assertEqual(self.project, loaded_group.project)

    def test_exception_all_members_not_enrolled_and_unenrolled_not_allowed(self):
        with self.assertRaises(ValidationError):
            SubmissionGroup.objects.validate_and_create(
                members=self.non_enrolled_group, project=self.project)

    def test_no_exception_on_all_members_not_enrolled_and_unenrolled_allowed(self):
        self.project.allow_submissions_from_non_enrolled_students = True
        self.project.save()

        group = SubmissionGroup.objects.validate_and_create(
            members=self.non_enrolled_group, project=self.project)

        loaded_group = SubmissionGroup.objects.get(pk=group.pk)

        self.assertEqual(group, loaded_group)
        self.assertCountEqual(
            self.non_enrolled_group, loaded_group.members.all())
        self.assertEqual(self.project, loaded_group.project)

    def test_exception_group_mix_of_enrolled_and_staff(self):
        self.project.max_group_size = 5
        self.project.save()
        with self.assertRaises(ValidationError):
            SubmissionGroup.objects.validate_and_create(
                members=self.staff_group + self.enrolled_group,
                project=self.project)

# -----------------------------------------------------------------------------
# -----------------------------------------------------------------------------
# -----------------------------------------------------------------------------


# class GroupQueryFunctionTests(TemporaryFilesystemTestCase):
#     def setUp(self):
#         super().setUp()

#         self.course = Course.objects.validate_and_create(name='eecs280')
#         self.semester = Semester.objects.validate_and_create(
#             name='f15', course=self.course)

#         self.project = Project.objects.validate_and_create(
#             name='my_project', semester=self.semester, max_group_size=5,
#             allow_submissions_from_non_enrolled_students=True)

#     def test_get_single_member_group(self):
#         group = SubmissionGroup.objects.validate_and_create(
#             members=['jameslp@umich.edu'], project=self.project)

#         self.assertEqual(
#             group,
#             SubmissionGroup.get_group(['jameslp@umich.edu'], self.project))

#     def test_get_multiple_member_group_exact(self):
#         members = [
#             'jameslp@umich.edu', 'awdeorio@umich.edu', 'jsatonik@umich.edu'
#         ]
#         group = SubmissionGroup.objects.validate_and_create(
#             members=members, project=self.project)

#         lookup = [
#             'jsatonik@umich.edu', 'jameslp@umich.edu', 'awdeorio@umich.edu'
#         ]
#         self.assertEqual(
#             group, SubmissionGroup.get_group(lookup, self.project))

#     def test_get_multiple_member_group_subset(self):
#         members = [
#             'jameslp@umich.edu', 'awdeorio@umich.edu', 'jsatonik@umich.edu'
#         ]
#         group = SubmissionGroup.objects.validate_and_create(
#             members=members, project=self.project)

#         lookup = [
#             'jsatonik@umich.edu', 'awdeorio@umich.edu'
#         ]
#         self.assertEqual(
#             group, SubmissionGroup.get_group(lookup, self.project))

#     def test_not_found_no_match(self):
#         members = [
#             'jameslp@umich.edu', 'awdeorio@umich.edu', 'jsatonik@umich.edu'
#         ]
#         SubmissionGroup.objects.validate_and_create(
#             members=members, project=self.project)

#         lookup = ['jjuett@umich.edu']
#         with self.assertRaises(ObjectDoesNotExist):
#             SubmissionGroup.get_group(lookup, self.project)

#     def test_not_found_partial_match(self):
#         members = [
#             'jameslp@umich.edu', 'awdeorio@umich.edu', 'jsatonik@umich.edu'
#         ]
#         SubmissionGroup.objects.validate_and_create(
#             members=members, project=self.project)

#         lookup = [
#             'jsatonik@umich.edu', 'jjuett@umich.edu'
#         ]
#         with self.assertRaises(ObjectDoesNotExist):
#             SubmissionGroup.get_group(lookup, self.project)
