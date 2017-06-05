import datetime
import os

from django.core import exceptions
from django.core.cache import cache
from django.http import Http404
from django.utils import timezone

import autograder.core.models as ag_models
import autograder.core.utils as core_ut
import autograder.utils.testing.model_obj_builders as obj_build
import autograder.utils.testing as test_ut


class _SetUp:
    def setUp(self):
        super().setUp()

        self.project = obj_build.build_project(
            project_kwargs={'max_group_size': 2})
        self.course = self.project.course

        self.enrolled_group = obj_build.create_dummy_users(2)
        self.course.enrolled_students.add(*self.enrolled_group)

        self.staff_group = obj_build.create_dummy_users(2)
        self.course.staff.add(*self.staff_group)

        self.non_enrolled_group = obj_build.create_dummy_users(2)


class MiscSubmissionGroupTestCase(_SetUp, test_ut.UnitTestBase):
    def test_serializable_fields(self):
        expected_fields = [
            'pk',
            'member_names',
            'project',
            'extended_due_date',

            'num_submits_towards_limit',
        ]

        self.assertCountEqual(
            expected_fields,
            ag_models.SubmissionGroup.get_serializable_fields())

        group = obj_build.build_submission_group()
        self.assertTrue(group.to_dict())

    def test_editable_fields(self):
        self.assertCountEqual(['extended_due_date'],
                              ag_models.SubmissionGroup.get_editable_fields())

    def test_valid_initialization_with_defaults(self):
        group = ag_models.SubmissionGroup.objects.validate_and_create(
            members=self.enrolled_group,
            project=self.project)

        group.refresh_from_db()

        self.assertIsNone(group.extended_due_date)
        self.assertCountEqual(
            self.enrolled_group, group.members.all())
        self.assertCountEqual(
            (user.username for user in self.enrolled_group),
            group.member_names)
        self.assertEqual(self.project, group.project)

        self.assertTrue(
            os.path.isdir(core_ut.get_student_submission_group_dir(group)))

    def test_valid_initialization_no_defaults(self):
        extended_due_date = timezone.now() + datetime.timedelta(days=1)
        group = ag_models.SubmissionGroup.objects.validate_and_create(
            members=self.enrolled_group,
            project=self.project,
            extended_due_date=extended_due_date)

        group.refresh_from_db()

        self.assertEqual(group.extended_due_date, extended_due_date)
        self.assertCountEqual(self.enrolled_group, group.members.all())
        self.assertEqual(self.project, group.project)

    def test_valid_member_of_multiple_groups_for_different_projects(self):
        other_project = obj_build.build_project(
            project_kwargs={
                'max_group_size': 2,
                'visible_to_guests': True})

        repeated_user = self.enrolled_group[0]

        first_group = ag_models.SubmissionGroup.objects.validate_and_create(
            members=self.enrolled_group,
            project=self.project)

        second_group = ag_models.SubmissionGroup.objects.validate_and_create(
            members=[repeated_user], project=other_project)

        first_group.refresh_from_db()
        self.assertCountEqual(
            self.enrolled_group, first_group.members.all())
        self.assertEqual(self.project, first_group.project)

        second_group.refresh_from_db()
        self.assertCountEqual(
            [repeated_user], second_group.members.all())
        self.assertEqual(other_project, second_group.project)

        groups = list(repeated_user.groups_is_member_of.all())
        self.assertCountEqual([first_group, second_group], groups)


# TODO: change to nonmember function defined elsewhere
class GetUltimateSubmissionTestCase(test_ut.UnitTestBase):
    def test_get_ultimate_submission(self):
        submissions, best, tests = obj_build.build_submissions_with_results(
            num_submissions=5, make_one_best=True)
        self.assertNotEqual(submissions[-1], best)
        group = best.submission_group
        project = group.project

        project.validate_and_update(
            ultimate_submission_policy=(
                ag_models.UltimateSubmissionPolicy.most_recent))
        self.assertEqual(submissions[-1], group.ultimate_submission)

        project.validate_and_update(
            ultimate_submission_policy=(
                ag_models.UltimateSubmissionPolicy.best))
        self.assertEqual(best, group.ultimate_submission)

    def test_get_ultimate_submission_high_score_tied_take_most_recent(self):
        submissions, tests = obj_build.build_submissions_with_results(
            num_submissions=4)
        group = submissions[0].submission_group
        project = group.project

        project.validate_and_update(
            ultimate_submission_policy=(
                ag_models.UltimateSubmissionPolicy.most_recent))
        self.assertEqual(submissions[-1], group.ultimate_submission)

        project.validate_and_update(
            ultimate_submission_policy=(
                ag_models.UltimateSubmissionPolicy.best))
        self.assertEqual(submissions[-1], group.ultimate_submission)

    def test_get_ultimate_submission_no_submissions(self):
        group = obj_build.build_submission_group()
        with self.assertRaises(Http404):
            group.ultimate_submission


class BestBasicSubmissionTestCase(test_ut.UnitTestBase):
    def test_best_basic_submission(self):
        cache.clear()
        # Increase these numbers when benchmarking
        num_submissions = 3
        num_tests = 5
        submissions, best, tests = obj_build.build_submissions_with_results(
            num_submissions=num_submissions, num_tests=num_tests,
            make_one_best=True)

        group = submissions[0].submission_group
        actual_num_tests = group.project.autograder_test_cases.count()
        self.assertEqual(num_tests, actual_num_tests)
        self.assertEqual(num_submissions, len(submissions))
        self.assertEqual(num_submissions,
                         best.submission_group.submissions.count())

        # # Benchmarks
        # for i in range(2):
        #     cache.clear()
        #     with test_ut.Timer('Max of {} submissions with {} tests from '
        #                   'empty cache.'.format(num_submissions, num_tests)):
        #         actual_best = group.submission_with_best_basic_score

        # for i in range(10):
        #     cache.delete_many(
        #         [sub.basic_score_cache_key for sub in submissions])
        #     with test_ut.Timer('Max of {} submissions with {} tests from '
        #                   'results cache.'.format(num_submissions, num_tests)):
        #         actual_best = group.submission_with_best_basic_score

        # for i in range(10):
        #     with test_ut.Timer('Max of {} submissions with {} tests from '
        #                   'submissions cache.'.format(num_submissions,
        #                                               num_tests)):
        #         actual_best = group.submission_with_best_basic_score

        self.assertEqual(best, group.submission_with_best_basic_score)


class SubmissionGroupSizeTestCase(_SetUp, test_ut.UnitTestBase):
    def test_valid_override_group_max_size(self):
        self.enrolled_group += obj_build.create_dummy_users(3)
        self.project.course.enrolled_students.add(*self.enrolled_group)
        group = ag_models.SubmissionGroup.objects.validate_and_create(
            members=self.enrolled_group,
            project=self.project,
            check_group_size_limits=False)

        group.refresh_from_db()

        self.assertCountEqual(self.enrolled_group, group.members.all())

    def test_valid_override_group_min_size(self):
        self.project.min_group_size = 10
        self.project.max_group_size = 10
        self.project.save()
        group = ag_models.SubmissionGroup.objects.validate_and_create(
            members=self.enrolled_group,
            project=self.project,
            check_group_size_limits=False)

        group.refresh_from_db()

        self.assertCountEqual(
            self.enrolled_group, group.members.all())

    def test_error_create_empty_group_with_override_size(self):
        with self.assertRaises(exceptions.ValidationError):
            ag_models.SubmissionGroup.objects.validate_and_create(
                members=[], project=self.project,
                check_group_size_limits=False)

    def test_exception_on_too_few_group_members(self):
        with self.assertRaises(exceptions.ValidationError):
            ag_models.SubmissionGroup.objects.validate_and_create(
                members=[], project=self.project)

        self.project.min_group_size = 2
        self.project.save()
        with self.assertRaises(exceptions.ValidationError):
            ag_models.SubmissionGroup.objects.validate_and_create(
                members=self.enrolled_group[0:1],
                project=self.project)

    def test_exception_on_too_many_group_members(self):
        self.project.save()

        new_user = obj_build.create_dummy_user()
        self.course.enrolled_students.add(new_user)
        self.enrolled_group.append(new_user)

        with self.assertRaises(exceptions.ValidationError):
            ag_models.SubmissionGroup.objects.validate_and_create(
                members=self.enrolled_group, project=self.project)


class UpdateSubmissionGroupTestCase(_SetUp, test_ut.UnitTestBase):
    def test_normal_update_group(self):
        group = ag_models.SubmissionGroup.objects.validate_and_create(
            members=self.enrolled_group,
            project=self.project)

        new_members = obj_build.create_dummy_users(2)
        self.project.course.enrolled_students.add(*new_members)

        group.validate_and_update(members=new_members)

        loaded_group = ag_models.SubmissionGroup.objects.get(pk=group.pk)
        self.assertCountEqual(new_members, loaded_group.members.all())

    def test_update_group_error_too_many_members(self):
        group = ag_models.SubmissionGroup.objects.validate_and_create(
            members=self.enrolled_group,
            project=self.project)

        new_members = obj_build.create_dummy_users(5)
        self.project.course.enrolled_students.add(*new_members)

        with self.assertRaises(exceptions.ValidationError) as cm:
            group.validate_and_update(members=new_members)

        self.assertTrue('members' in cm.exception.message_dict)

    def test_update_group_error_too_few_members(self):
        group = ag_models.SubmissionGroup.objects.validate_and_create(
            members=self.enrolled_group,
            project=self.project)

        new_members = obj_build.create_dummy_users(2)
        self.project.course.enrolled_students.add(*new_members)

        self.project.min_group_size = 10
        self.project.max_group_size = 10
        self.project.save()

        with self.assertRaises(exceptions.ValidationError) as cm:
            group.validate_and_update(members=new_members)

        self.assertTrue('members' in cm.exception.message_dict)

    def test_update_group_override_min_size(self):
        group = ag_models.SubmissionGroup.objects.validate_and_create(
            members=self.enrolled_group,
            project=self.project)

        self.project.min_group_size = 10
        self.project.max_group_size = 10
        self.project.save()

        new_members = obj_build.create_dummy_users(2)
        self.project.course.enrolled_students.add(*new_members)
        group.validate_and_update(members=new_members,
                                  check_group_size_limits=False)

        group.refresh_from_db()

        self.assertCountEqual(new_members, group.members.all())

    def test_update_group_override_max_size(self):
        group = ag_models.SubmissionGroup.objects.validate_and_create(
            members=self.enrolled_group,
            project=self.project)

        new_members = obj_build.create_dummy_users(5)
        self.project.course.enrolled_students.add(*new_members)

        group.validate_and_update(members=new_members,
                                  check_group_size_limits=False)

        group.refresh_from_db()

        self.assertCountEqual(new_members, group.members.all())

    def test_error_update_empty_group_with_override_size(self):
        group = ag_models.SubmissionGroup.objects.validate_and_create(
            members=self.enrolled_group,
            project=self.project)

        with self.assertRaises(exceptions.ValidationError):
            group.validate_and_update(members=[],
                                      check_group_size_limits=False)


class GroupMembershipTestCase(_SetUp, test_ut.UnitTestBase):
    def test_exception_on_group_member_already_in_another_group(self):
        ag_models.SubmissionGroup.objects.validate_and_create(
            members=self.enrolled_group[0:1], project=self.project)

        with self.assertRaises(exceptions.ValidationError):
            ag_models.SubmissionGroup.objects.validate_and_create(
                members=self.enrolled_group, project=self.project)

    def test_exception_on_some_members_not_enrolled(self):
        mixed_group = self.enrolled_group[0:1] + [obj_build.create_dummy_user()]
        with self.assertRaises(exceptions.ValidationError):
            ag_models.SubmissionGroup.objects.validate_and_create(
                members=mixed_group, project=self.project)

        self.project.visible_to_guests = True
        self.project.save()

        with self.assertRaises(exceptions.ValidationError):
            ag_models.SubmissionGroup.objects.validate_and_create(
                members=mixed_group, project=self.project)

    def test_no_exception_group_of_staff_members(self):
        group = ag_models.SubmissionGroup.objects.validate_and_create(
            members=self.staff_group, project=self.project)

        group.refresh_from_db()

        self.assertCountEqual(self.staff_group, group.members.all())
        self.assertEqual(self.project, group.project)

    def test_exception_all_members_not_enrolled_and_unenrolled_not_allowed(self):
        with self.assertRaises(exceptions.ValidationError):
            ag_models.SubmissionGroup.objects.validate_and_create(
                members=self.non_enrolled_group, project=self.project)

    def test_no_exception_on_all_members_not_enrolled_and_unenrolled_allowed(self):
        self.project.visible_to_guests = True
        self.project.save()

        group = ag_models.SubmissionGroup.objects.validate_and_create(
            members=self.non_enrolled_group, project=self.project)

        group.refresh_from_db()

        self.assertCountEqual(self.non_enrolled_group, group.members.all())
        self.assertEqual(self.project, group.project)

    def test_exception_group_mix_of_enrolled_and_staff(self):
        self.project.max_group_size = 5
        self.project.save()
        with self.assertRaises(exceptions.ValidationError):
            ag_models.SubmissionGroup.objects.validate_and_create(
                members=self.staff_group + self.enrolled_group,
                project=self.project)
