import datetime
import os
import random
from unittest import mock

from django.contrib.auth.models import User
from django.core import exceptions
from django.utils import timezone
import pytz

import autograder.core.models as ag_models
import autograder.core.utils as core_ut
import autograder.utils.testing as test_ut
import autograder.utils.testing.model_obj_builders as obj_build
from autograder.utils.testing import UnitTestBase


class _SetUp(test_ut.UnitTestBase):
    def setUp(self):
        super().setUp()

        self.project = obj_build.make_project(max_group_size=2)
        self.course = self.project.course

        self.student_users = unsorted_users(obj_build.make_student_users(self.course, 2))
        self.staff_users = unsorted_users(obj_build.make_staff_users(self.course, 2))
        self.guest_group = obj_build.make_users(2)


def sorted_users(users):
    return list(sorted(users, key=lambda user: user.username))


def unsorted_users(users):
    random.shuffle(users)
    return users


class GroupTestCase(_SetUp):
    def test_valid_initialization_with_defaults(self):
        group = ag_models.Group.objects.validate_and_create(
            members=self.student_users,
            project=self.project)

        group.refresh_from_db()

        self.assertIsNone(group.extended_due_date)
        self.assertCountEqual(self.student_users, group.members.all())
        self.assertSequenceEqual([user.username for user in sorted_users(self.student_users)],
                                 group.member_names)
        self.assertEqual(self.project, group.project)
        self.assertEqual({}, group.late_days_used)

        self.assertTrue(os.path.isdir(core_ut.get_student_group_dir(group)))

    def test_valid_initialization_no_defaults(self):
        extended_due_date = timezone.now() + datetime.timedelta(days=1)
        group = ag_models.Group.objects.validate_and_create(
            members=self.student_users,
            project=self.project,
            extended_due_date=extended_due_date,
        )

        group.refresh_from_db()

        self.assertEqual(group.extended_due_date, extended_due_date)
        self.assertCountEqual(self.student_users, group.members.all())
        self.assertEqual(self.project, group.project)

    def test_valid_member_of_multiple_groups_for_different_projects(self):
        other_project = obj_build.build_project(
            project_kwargs={
                'max_group_size': 2,
                'guests_can_submit': True})

        repeated_user = self.student_users[0]

        first_group = ag_models.Group.objects.validate_and_create(
            members=self.student_users, project=self.project)

        second_group = ag_models.Group.objects.validate_and_create(
            members=[repeated_user], project=other_project)

        first_group.refresh_from_db()
        self.assertCountEqual(self.student_users, first_group.members.all())
        self.assertEqual(self.project, first_group.project)

        second_group.refresh_from_db()
        self.assertCountEqual([repeated_user], second_group.members.all())
        self.assertEqual(other_project, second_group.project)

        groups = list(repeated_user.groups_is_member_of.all())
        self.assertCountEqual([first_group, second_group], groups)

    def test_groups_sorted_by_usernames(self):
        self.project.validate_and_update(guests_can_submit=True)

        # Usernames matter here!
        group1_members = [User.objects.create(username='ggg'), User.objects.create(username='hhh')]
        group2_members = [User.objects.create(username='aaa'), User.objects.create(username='eee')]
        group3_members = [User.objects.create(username='fff'), User.objects.create(username='ccc')]
        group4_members = [User.objects.create(username='ddd'), User.objects.create(username='bbb')]

        group1 = ag_models.Group.objects.validate_and_create(
            members=group1_members, project=self.project)
        group2 = ag_models.Group.objects.validate_and_create(
            members=group2_members, project=self.project)
        group3 = ag_models.Group.objects.validate_and_create(
            members=group3_members, project=self.project)
        group4 = ag_models.Group.objects.validate_and_create(
            members=group4_members, project=self.project)

        self.assertSequenceEqual([group2, group4, group3, group1],
                                 ag_models.Group.objects.all())

    def test_bonus_submissions_remaining_init(self):
        num_bonus_submissions = 5
        self.project.validate_and_update(num_bonus_submissions=num_bonus_submissions)
        group = ag_models.Group.objects.validate_and_create(
            members=self.student_users, project=self.project)
        self.assertEqual(num_bonus_submissions, group.bonus_submissions_remaining)

        # Make sure bonus_submissions_remaining doesn't change on save
        bonus_submissions_remaining = 1
        group.validate_and_update(bonus_submissions_remaining=bonus_submissions_remaining)
        group.save()
        self.assertEqual(bonus_submissions_remaining, group.bonus_submissions_remaining)

    def test_num_submits_towards_limit(self):
        group = ag_models.Group.objects.validate_and_create(
            members=self.student_users,
            project=self.project)

        num_submissions = 4
        for i in range(num_submissions):
            ag_models.Submission.objects.validate_and_create(submitted_files=[], group=group)
        group.refresh_from_db()
        self.assertEqual(num_submissions, group.num_submissions)
        self.assertEqual(num_submissions, group.num_submits_towards_limit)

    def test_num_submits_towards_limit_dst_edge_case(self):
        reset_timezone = 'US/Eastern'
        submissions_per_day = 3
        self.project.validate_and_update(
            submission_limit_reset_time=datetime.time(0, 0, 0),
            submission_limit_reset_timezone=reset_timezone,
            submission_limit_per_day=submissions_per_day
        )

        group = ag_models.Group.objects.validate_and_create(
            members=self.student_users,
            project=self.project)

        current_time = datetime.datetime(2022, 3, 13, 11, tzinfo=pytz.timezone('UTC'))

        with mock.patch('autograder.core.models.group.group.timezone.now',
                        new=lambda: current_time):
            self.assertEqual(0, group.num_submits_towards_limit)
            for i in range(submissions_per_day):
                ag_models.Submission.objects.validate_and_create(submitted_files=[], group=group)

            self.assertEqual(submissions_per_day, group.num_submits_towards_limit)

        # Still a few hours before the reset time
        current_time = datetime.datetime(2022, 3, 14, 1, tzinfo=pytz.timezone('UTC'))
        with mock.patch('autograder.core.models.group.group.timezone.now',
                        new=lambda: current_time):
            self.assertEqual(submissions_per_day, group.num_submits_towards_limit)

        # 30 min before the reset time
        current_time = datetime.datetime(2022, 3, 14, 3, 30, tzinfo=pytz.timezone('UTC'))
        with mock.patch('autograder.core.models.group.group.timezone.now',
                        new=lambda: current_time):
            self.assertEqual(submissions_per_day, group.num_submits_towards_limit)

        # 30 min after the reset time (which is at UTC 4:00 instead of 5:00 because of DST)
        current_time = datetime.datetime(2022, 3, 14, 4, 30, tzinfo=pytz.timezone('UTC'))
        with mock.patch('autograder.core.models.group.group.timezone.now',
                        new=lambda: current_time):
            self.assertEqual(0, group.num_submits_towards_limit)

    def test_bonus_submission_counts_towards_limit(self):
        self.project.validate_and_update(
            num_bonus_submissions=1,
            submission_limit_per_day=1
        )
        group: ag_models.Group = ag_models.Group.objects.validate_and_create(
            members=self.student_users, project=self.project)

        regular_submission = obj_build.make_finished_submission(group=group)
        bonus_submission = obj_build.make_finished_submission(
            group=group, is_bonus_submission=True)
        past_limit_submission = obj_build.make_finished_submission(
            group=group, is_past_daily_limit=True)

        self.assertEqual(3, group.num_submits_towards_limit)

    def test_serializable_fields(self):
        expected_fields = [
            'pk',
            'member_names',
            'members',
            'project',
            'extended_due_date',

            'bonus_submissions_remaining',

            'late_days_used',

            'num_submits_towards_limit',
            'num_submissions',

            'created_at',
            'last_modified',
        ]

        group = obj_build.build_group()
        serialized = group.to_dict()
        self.assertCountEqual(expected_fields, list(serialized.keys()))
        self.assertIsInstance(serialized['members'], list)
        self.assertIsInstance(serialized['members'][0], dict)

    def test_editable_fields(self):
        self.assertCountEqual(['extended_due_date', 'bonus_submissions_remaining'],
                              ag_models.Group.get_editable_fields())


class BonusSubmissionTokenCountTestCase(test_ut.UnitTestBase):
    def setUp(self):
        super().setUp()
        self.project = obj_build.make_project(num_bonus_submissions=4)
        self.course = self.project.course

        self.no_tokens_used_group = obj_build.make_group(project=self.project)

        self.some_tokens_used_group = obj_build.make_group(project=self.project)
        self.some_tokens_used_group.bonus_submissions_used = 3
        self.some_tokens_used_group.save()

        self.all_tokens_used_group = obj_build.make_group(project=self.project)
        self.all_tokens_used_group.bonus_submissions_used = 4
        self.all_tokens_used_group.save()

    def test_individual_group_given_extra_tokens(self) -> None:
        self.assertEqual(4, self.no_tokens_used_group.bonus_submissions_remaining)
        self.no_tokens_used_group.validate_and_update(bonus_submissions_remaining=5)
        self.no_tokens_used_group.refresh_from_db()
        self.assertEqual(5, self.no_tokens_used_group.bonus_submissions_remaining)
        self.assertEqual(0, self.no_tokens_used_group.bonus_submissions_used)

        self.assertEqual(1, self.some_tokens_used_group.bonus_submissions_remaining)
        self.some_tokens_used_group.validate_and_update(bonus_submissions_remaining=2)
        self.some_tokens_used_group.refresh_from_db()
        self.assertEqual(2, self.some_tokens_used_group.bonus_submissions_remaining)
        self.assertEqual(3, self.some_tokens_used_group.bonus_submissions_used)

        self.assertEqual(0, self.all_tokens_used_group.bonus_submissions_remaining)
        self.all_tokens_used_group.validate_and_update(bonus_submissions_remaining=3)
        self.all_tokens_used_group.refresh_from_db()
        self.assertEqual(3, self.all_tokens_used_group.bonus_submissions_remaining)
        self.assertEqual(4, self.all_tokens_used_group.bonus_submissions_used)

    def test_individual_group_tokens_given_extra_and_revoked(self) -> None:
        self.assertEqual(4, self.no_tokens_used_group.bonus_submissions_remaining)
        self.no_tokens_used_group.validate_and_update(bonus_submissions_remaining=6)
        self.no_tokens_used_group.refresh_from_db()

        self.assertEqual(6, self.no_tokens_used_group.bonus_submissions_remaining)
        self.no_tokens_used_group.validate_and_update(bonus_submissions_remaining=3)
        self.no_tokens_used_group.refresh_from_db()
        self.assertEqual(3, self.no_tokens_used_group.bonus_submissions_remaining)
        self.assertEqual(0, self.no_tokens_used_group.bonus_submissions_used)

    def test_individual_group_tokens_revoked_then_given_extra(self) -> None:
        self.assertEqual(4, self.no_tokens_used_group.bonus_submissions_remaining)
        self.no_tokens_used_group.validate_and_update(bonus_submissions_remaining=3)
        self.no_tokens_used_group.refresh_from_db()

        self.assertEqual(3, self.no_tokens_used_group.bonus_submissions_remaining)
        self.no_tokens_used_group.validate_and_update(bonus_submissions_remaining=5)
        self.no_tokens_used_group.refresh_from_db()
        self.assertEqual(5, self.no_tokens_used_group.bonus_submissions_remaining)

    def test_bonus_submissions_remaining_set_to_zero(self) -> None:
        self.some_tokens_used_group.validate_and_update(bonus_submissions_remaining=0)
        self.some_tokens_used_group.refresh_from_db()
        self.assertEqual(0, self.some_tokens_used_group.bonus_submissions_remaining)
        self.assertEqual(3, self.some_tokens_used_group.bonus_submissions_used)

    def test_invalid_set_bonus_submissions_remaining_to_be_negative(self) -> None:
        with self.assertRaises(exceptions.ValidationError) as cm:
            self.some_tokens_used_group.validate_and_update(
                bonus_submissions_remaining=-1)

        self.assertIn('bonus_submissions_remaining', cm.exception.message_dict)

    def test_individual_group_given_extra_tokens_twice(self) -> None:
        self.some_tokens_used_group.validate_and_update(bonus_submissions_remaining=2)
        self.some_tokens_used_group.refresh_from_db()
        self.assertEqual(2, self.some_tokens_used_group.bonus_submissions_remaining)
        self.assertEqual(3, self.some_tokens_used_group.bonus_submissions_used)

        self.some_tokens_used_group.validate_and_update(bonus_submissions_remaining=3)
        self.some_tokens_used_group.refresh_from_db()
        self.assertEqual(3, self.some_tokens_used_group.bonus_submissions_remaining)
        self.assertEqual(3, self.some_tokens_used_group.bonus_submissions_used)

    def test_project_token_count_lowered_then_raised(self) -> None:
        self.assertEqual(0, self.all_tokens_used_group.bonus_submissions_remaining)
        self.assertEqual(1, self.some_tokens_used_group.bonus_submissions_remaining)
        self.assertEqual(4, self.no_tokens_used_group.bonus_submissions_remaining)

        self.project.validate_and_update(
            num_bonus_submissions=self.project.num_bonus_submissions - 2)

        self.no_tokens_used_group.refresh_from_db()
        self.some_tokens_used_group.refresh_from_db()
        self.all_tokens_used_group.refresh_from_db()

        self.assertEqual(0, self.all_tokens_used_group.bonus_submissions_remaining)
        self.assertEqual(0, self.some_tokens_used_group.bonus_submissions_remaining)
        self.assertEqual(2, self.no_tokens_used_group.bonus_submissions_remaining)

        self.project.validate_and_update(
            num_bonus_submissions=self.project.num_bonus_submissions + 3)

        self.no_tokens_used_group.refresh_from_db()
        self.some_tokens_used_group.refresh_from_db()
        self.all_tokens_used_group.refresh_from_db()

        self.assertEqual(1, self.all_tokens_used_group.bonus_submissions_remaining)
        self.assertEqual(2, self.some_tokens_used_group.bonus_submissions_remaining)
        self.assertEqual(5, self.no_tokens_used_group.bonus_submissions_remaining)

    def test_project_token_count_lowered_then_group_granted_extra(self) -> None:
        self.assertEqual(0, self.all_tokens_used_group.bonus_submissions_remaining)
        self.project.validate_and_update(
            num_bonus_submissions=self.project.num_bonus_submissions - 2)
        self.all_tokens_used_group.refresh_from_db()

        self.assertEqual(0, self.all_tokens_used_group.bonus_submissions_remaining)
        self.all_tokens_used_group.validate_and_update(bonus_submissions_remaining=2)
        self.all_tokens_used_group.refresh_from_db()
        self.assertEqual(2, self.all_tokens_used_group.bonus_submissions_remaining)

        # If we re-raise the project count, the group's count should go up
        # by the same amount
        self.project.validate_and_update(
            num_bonus_submissions=self.project.num_bonus_submissions + 3)
        self.all_tokens_used_group.refresh_from_db()
        self.assertEqual(5, self.all_tokens_used_group.bonus_submissions_remaining)


class GroupSizeTestCase(_SetUp):
    def test_valid_override_group_max_size(self):
        self.student_users += obj_build.create_dummy_users(3)
        self.project.course.students.add(*self.student_users)
        group = ag_models.Group.objects.validate_and_create(
            members=self.student_users,
            project=self.project,
            check_group_size_limits=False)

        group.refresh_from_db()

        self.assertCountEqual(self.student_users, group.members.all())

    def test_valid_override_group_min_size(self):
        self.project.min_group_size = 10
        self.project.max_group_size = 10
        self.project.save()
        group = ag_models.Group.objects.validate_and_create(
            members=self.student_users,
            project=self.project,
            check_group_size_limits=False)

        group.refresh_from_db()

        self.assertCountEqual(self.student_users, group.members.all())

    def test_error_create_empty_group_with_override_size(self):
        with self.assertRaises(exceptions.ValidationError):
            ag_models.Group.objects.validate_and_create(
                members=[], project=self.project,
                check_group_size_limits=False)

    def test_exception_on_too_few_group_members(self):
        with self.assertRaises(exceptions.ValidationError):
            ag_models.Group.objects.validate_and_create(
                members=[], project=self.project)

        self.project.min_group_size = 2
        self.project.save()
        with self.assertRaises(exceptions.ValidationError):
            ag_models.Group.objects.validate_and_create(
                members=self.student_users[0:1],
                project=self.project)

    def test_exception_on_too_many_group_members(self):
        self.project.save()

        new_user = obj_build.create_dummy_user()
        self.course.students.add(new_user)
        self.student_users.append(new_user)

        with self.assertRaises(exceptions.ValidationError):
            ag_models.Group.objects.validate_and_create(
                members=self.student_users, project=self.project)


class UpdateGroupTestCase(_SetUp):
    def test_normal_update_group(self):
        group = ag_models.Group.objects.validate_and_create(
            members=self.student_users,
            project=self.project)

        new_members = unsorted_users(obj_build.make_student_users(self.course, 2))

        group.validate_and_update(members=new_members)

        loaded_group = ag_models.Group.objects.get(pk=group.pk)
        self.assertCountEqual(new_members, loaded_group.members.all())
        self.assertSequenceEqual([user.username for user in sorted_users(new_members)],
                                 loaded_group.member_names)

    def test_update_group_error_too_many_members(self):
        group = ag_models.Group.objects.validate_and_create(
            members=self.student_users,
            project=self.project)

        new_members = obj_build.create_dummy_users(5)
        self.project.course.students.add(*new_members)

        with self.assertRaises(exceptions.ValidationError) as cm:
            group.validate_and_update(members=new_members)

        self.assertTrue('members' in cm.exception.message_dict)

    def test_update_group_error_too_few_members(self):
        group = ag_models.Group.objects.validate_and_create(
            members=self.student_users,
            project=self.project)

        new_members = obj_build.create_dummy_users(2)
        self.project.course.students.add(*new_members)

        self.project.min_group_size = 10
        self.project.max_group_size = 10
        self.project.save()

        with self.assertRaises(exceptions.ValidationError) as cm:
            group.validate_and_update(members=new_members)

        self.assertTrue('members' in cm.exception.message_dict)

    def test_update_group_override_min_size(self):
        group = ag_models.Group.objects.validate_and_create(
            members=self.student_users,
            project=self.project)

        self.project.min_group_size = 10
        self.project.max_group_size = 10
        self.project.save()

        new_members = obj_build.create_dummy_users(2)
        self.project.course.students.add(*new_members)
        group.validate_and_update(members=new_members,
                                  check_group_size_limits=False)

        group.refresh_from_db()

        self.assertCountEqual(new_members, group.members.all())

    def test_update_group_override_max_size(self):
        group = ag_models.Group.objects.validate_and_create(
            members=self.student_users,
            project=self.project)

        new_members = obj_build.create_dummy_users(5)
        self.project.course.students.add(*new_members)

        group.validate_and_update(members=new_members,
                                  check_group_size_limits=False)

        group.refresh_from_db()

        self.assertCountEqual(new_members, group.members.all())

    def test_error_update_empty_group_with_override_size(self):
        group = ag_models.Group.objects.validate_and_create(
            members=self.student_users,
            project=self.project)

        with self.assertRaises(exceptions.ValidationError):
            group.validate_and_update(members=[],
                                      check_group_size_limits=False)


class UpdateGroupMemberRolesTestCase(UnitTestBase):
    def setUp(self):
        super().setUp()

        self.course = obj_build.make_course()
        self.project = obj_build.make_project(
            course=self.course, max_group_size=2, guests_can_submit=True)

        self.group = obj_build.make_group(
            project=self.project, num_members=2, members_role=obj_build.UserRole.student)

    def test_valid_all_guests_any_domain(self):
        self.group.validate_and_update(
            members=[User.objects.create(username='llama@llama.edu'),
                     obj_build.make_user()])

    def test_exception_guests_not_allowed(self):
        self.project.validate_and_update(guests_can_submit=False)

        with self.assertRaises(exceptions.ValidationError):
            self.group.validate_and_update(members=[obj_build.make_user()])

    def test_all_members_allowed_domain(self):
        self.course.validate_and_update(allowed_guest_domain='@llama.edu')
        self.group.validate_and_update(
            members=[obj_build.make_allowed_domain_guest_user(self.course),
                     obj_build.make_allowed_domain_guest_user(self.course)])

    def test_exception_some_members_not_allowed_domain(self):
        self.course.validate_and_update(allowed_guest_domain='@llama.edu')
        with self.assertRaises(exceptions.ValidationError):
            self.group.validate_and_update(
                members=[obj_build.make_allowed_domain_guest_user(self.course),
                         obj_build.make_user()])

    def test_exception_no_members_allowed_domain(self):
        self.course.validate_and_update(allowed_guest_domain='@llama.edu')
        with self.assertRaises(exceptions.ValidationError):
            self.group.validate_and_update(
                members=[obj_build.make_user(), obj_build.make_user()])

    def test_exception_group_mix_of_student_and_staff(self):
        with self.assertRaises(exceptions.ValidationError):
            self.group.validate_and_update(
                members=[obj_build.make_student_user(self.course),
                         obj_build.make_staff_user(self.course)])

    def test_exception_some_students_some_guests(self):
        with self.assertRaises(exceptions.ValidationError):
            self.group.validate_and_update(
                members=[obj_build.make_student_user(self.course),
                         obj_build.make_user()])


class GroupMembershipTestCase(_SetUp):
    def test_exception_on_group_member_already_in_another_group(self):
        ag_models.Group.objects.validate_and_create(
            members=self.student_users[0:1], project=self.project)

        with self.assertRaises(exceptions.ValidationError):
            ag_models.Group.objects.validate_and_create(
                members=self.student_users, project=self.project)

    def test_exception_on_some_members_not_student(self):
        mixed_group = self.student_users[0:1] + [obj_build.create_dummy_user()]
        with self.assertRaises(exceptions.ValidationError):
            ag_models.Group.objects.validate_and_create(
                members=mixed_group, project=self.project)

        self.project.guests_can_submit = True
        self.project.save()

        with self.assertRaises(exceptions.ValidationError):
            ag_models.Group.objects.validate_and_create(
                members=mixed_group, project=self.project)

    def test_no_exception_group_of_staff_members(self):
        group = ag_models.Group.objects.validate_and_create(
            members=self.staff_users, project=self.project)

        group.refresh_from_db()

        self.assertCountEqual(self.staff_users, group.members.all())
        self.assertEqual(self.project, group.project)

    def test_exception_all_members_not_student_and_guests_not_allowed(self):
        with self.assertRaises(exceptions.ValidationError):
            ag_models.Group.objects.validate_and_create(
                members=self.guest_group, project=self.project)

    def test_all_members_allowed_domain(self):
        self.project.validate_and_update(guests_can_submit=True)
        self.project.course.validate_and_update(allowed_guest_domain='@llama.edu')

        ag_models.Group.objects.validate_and_create(
            project=self.project,
            members=[obj_build.make_allowed_domain_guest_user(self.course),
                     obj_build.make_allowed_domain_guest_user(self.course)])

    def test_exception_some_members_not_allowed_domain(self):
        self.project.validate_and_update(guests_can_submit=True)
        self.project.course.validate_and_update(allowed_guest_domain='@llama.edu')

        with self.assertRaises(exceptions.ValidationError):
            ag_models.Group.objects.validate_and_create(
                members=[obj_build.make_user(),
                         obj_build.make_allowed_domain_guest_user(self.course)],
                project=self.project)

    def test_exception_no_members_allowed_domain(self):
        self.project.validate_and_update(guests_can_submit=True)
        self.project.course.validate_and_update(allowed_guest_domain='@llama.edu')

        with self.assertRaises(exceptions.ValidationError):
            ag_models.Group.objects.validate_and_create(
                members=[obj_build.make_user(), obj_build.make_user()],
                project=self.project)

    def test_no_exception_on_all_members_not_student_and_guests_allowed(self):
        self.project.guests_can_submit = True
        self.project.save()

        group = ag_models.Group.objects.validate_and_create(
            members=self.guest_group, project=self.project)

        group.refresh_from_db()

        self.assertCountEqual(self.guest_group, group.members.all())
        self.assertEqual(self.project, group.project)

    def test_exception_group_mix_of_student_and_staff(self):
        self.project.max_group_size = 5
        self.project.save()
        with self.assertRaises(exceptions.ValidationError):
            ag_models.Group.objects.validate_and_create(
                members=self.staff_users + self.student_users,
                project=self.project)
