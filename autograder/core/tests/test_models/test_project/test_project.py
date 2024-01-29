import copy
import datetime
import os
import random

from django.core import exceptions
from django.utils import timezone

import autograder.core.models as ag_models
import autograder.core.utils as core_ut
import autograder.handgrading.models as hg_models
import autograder.utils.testing.model_obj_builders as obj_build
from autograder.utils.testing import UnitTestBase


class ProjectMiscTestCase(UnitTestBase):
    def setUp(self):
        super().setUp()

        self.course = obj_build.build_course()
        self.project_name = 'my_project'

    def test_valid_create_with_defaults(self):
        new_project: ag_models.Project = ag_models.Project.objects.validate_and_create(
            name=self.project_name, course=self.course)

        new_project.refresh_from_db()

        self.assertEqual(new_project, new_project)
        self.assertEqual(new_project.name, self.project_name)
        self.assertEqual(new_project.course, self.course)

        self.assertFalse(new_project.visible_to_students)
        self.assertIsNone(new_project.closing_time)
        self.assertIsNone(new_project.soft_closing_time)
        self.assertFalse(new_project.disallow_student_submissions)
        self.assertFalse(new_project.disallow_group_registration)
        self.assertFalse(new_project.guests_can_submit)
        self.assertEqual(new_project.min_group_size, 1)
        self.assertEqual(new_project.max_group_size, 1)

        self.assertIsNone(new_project.submission_limit_per_day)
        self.assertFalse(new_project.groups_combine_daily_submissions)
        self.assertEqual(True, new_project.allow_submissions_past_limit)
        self.assertEqual(datetime.time(),
                         new_project.submission_limit_reset_time)
        self.assertEqual('UTC', new_project.submission_limit_reset_timezone)
        self.assertEqual(0, new_project.num_bonus_submissions)

        self.assertIsNone(new_project.total_submission_limit)

        self.assertFalse(new_project.allow_late_days)

        self.assertTrue(new_project.hide_ultimate_submission_fdbk)
        self.assertEqual(
            ag_models.UltimateSubmissionPolicy.most_recent,
            new_project.ultimate_submission_policy)

        self.assertFalse(new_project.use_honor_pledge)
        self.assertEqual('', new_project.honor_pledge_text)

    def test_valid_create_non_defaults(self):
        tomorrow_date = timezone.now() + datetime.timedelta(days=1)
        soft_closing_time = tomorrow_date - timezone.timedelta(minutes=3)
        min_group_size = 2
        max_group_size = 5

        sub_limit = random.randint(1, 5)
        reset_time = datetime.time(8, 0, 0)

        selection_method = ag_models.UltimateSubmissionPolicy.best
        kwargs = {
            'name': self.project_name,
            'course': self.course,
            'visible_to_students': True,
            'closing_time': tomorrow_date,
            'soft_closing_time': soft_closing_time,
            'disallow_student_submissions': True,
            'disallow_group_registration': True,
            'guests_can_submit': True,
            'min_group_size': min_group_size,
            'max_group_size': max_group_size,

            'submission_limit_per_day': sub_limit,
            'groups_combine_daily_submissions': True,
            'allow_submissions_past_limit': False,
            'submission_limit_reset_time': reset_time,
            'submission_limit_reset_timezone': 'America/Chicago',
            'num_bonus_submissions': 3,

            'allow_late_days': True,

            'total_submission_limit': 4,

            'hide_ultimate_submission_fdbk': False,
            'ultimate_submission_policy': selection_method,

            'use_honor_pledge': True,
            'honor_pledge_text': 'Some honorable text',
        }

        new_project = ag_models.Project.objects.validate_and_create(**kwargs)

        kwargs['closing_time'] = kwargs['closing_time'].replace(second=0, microsecond=0)
        kwargs['soft_closing_time'] = kwargs['soft_closing_time'].replace(second=0, microsecond=0)
        new_project.refresh_from_db()

        for field_name, value in kwargs.items():
            self.assertEqual(value, getattr(new_project, field_name), msg=field_name)

    def test_has_handgrading_rubric(self):
        project: ag_models.Project = ag_models.Project.objects.validate_and_create(
            name=self.project_name, course=self.course)
        self.assertFalse(project.has_handgrading_rubric)

        hg_models.HandgradingRubric.objects.validate_and_create(project=project)
        project.refresh_from_db()
        self.assertTrue(project.has_handgrading_rubric)

        project.handgrading_rubric.delete()
        project.refresh_from_db()
        self.assertFalse(project.has_handgrading_rubric)

    def test_serialize(self):
        project = ag_models.Project.objects.validate_and_create(
            name='qeiruqioewiur', course=self.course
        )  # type: ag_models.Project
        instructor_file = obj_build.make_instructor_file(project)
        student_file = ag_models.ExpectedStudentFile.objects.validate_and_create(
            project=project, pattern='qweiourqpweioru')

        project_dict = project.to_dict()

        expected_keys = [
            'pk',
            'name',
            'course',
            'last_modified',
            'visible_to_students',
            'closing_time',
            'soft_closing_time',
            'disallow_student_submissions',
            'disallow_group_registration',
            'guests_can_submit',
            'min_group_size',
            'max_group_size',

            'submission_limit_per_day',
            'allow_submissions_past_limit',
            'groups_combine_daily_submissions',
            'submission_limit_reset_time',
            'submission_limit_reset_timezone',
            'num_bonus_submissions',

            'total_submission_limit',

            'allow_late_days',

            'ultimate_submission_policy',
            'hide_ultimate_submission_fdbk',

            'instructor_files',
            'expected_student_files',

            'has_handgrading_rubric',

            'send_email_on_submission_received',
            'send_email_on_non_deferred_tests_finished',

            'use_honor_pledge',
            'honor_pledge_text',
        ]
        self.assertCountEqual(expected_keys, project_dict.keys())
        self.assertEqual('UTC', project_dict['submission_limit_reset_timezone'])

        self.assertSequenceEqual([instructor_file.to_dict()], project_dict['instructor_files'])
        self.assertSequenceEqual([student_file.to_dict()],
                                 project_dict['expected_student_files'])

        update_dict = copy.deepcopy(project_dict)
        non_editable = [
            'pk',
            'course',
            'last_modified',
            'instructor_files',
            'expected_student_files',
            'has_handgrading_rubric',
        ]
        for field in non_editable:
            update_dict.pop(field)
        project.validate_and_update(**update_dict)

        other_timezone = 'America/Chicago'
        project.validate_and_update(submission_limit_reset_timezone=other_timezone)
        project.refresh_from_db()
        self.assertEqual(other_timezone, project.to_dict()['submission_limit_reset_timezone'])


class HardAndSoftClosingTimeTestCase(UnitTestBase):
    def setUp(self):
        super().setUp()
        self.course = obj_build.build_course()

    def test_valid_soft_closing_time_None_closing_time_not_None(self):
        closing_time = timezone.now()
        proj = ag_models.Project.objects.validate_and_create(
            name='stave', course=self.course,
            closing_time=closing_time,
            soft_closing_time=None)

        proj.refresh_from_db()
        self.assertEqual(closing_time.replace(second=0, microsecond=0), proj.closing_time)
        self.assertIsNone(proj.soft_closing_time)

    def test_error_soft_closing_time_after_closing_time(self):
        closing_time = timezone.now()
        soft_closing_time = closing_time + timezone.timedelta(minutes=5)
        with self.assertRaises(exceptions.ValidationError) as cm:
            ag_models.Project.objects.validate_and_create(
                name='stove', course=self.course,
                closing_time=closing_time,
                soft_closing_time=soft_closing_time)

        self.assertIn('soft_closing_time', cm.exception.message_dict)


class ProjectMiscErrorTestCase(UnitTestBase):
    def setUp(self):
        super().setUp()
        self.course = obj_build.build_course()

    def test_error_negative_submission_limit_per_day(self):
        with self.assertRaises(exceptions.ValidationError) as cm:
            ag_models.Project.objects.validate_and_create(
                name='steve', course=self.course,
                submission_limit_per_day=random.randint(-10, -1))

        self.assertIn('submission_limit_per_day', cm.exception.message_dict)

    def test_error_invalid_ultimate_submission_policy(self):
        with self.assertRaises(exceptions.ValidationError) as cm:
            ag_models.Project.objects.validate_and_create(
                name='steve', course=self.course,
                ultimate_submission_policy='not_a_method')

        self.assertIn('ultimate_submission_policy',
                      cm.exception.message_dict)

    def test_error_zero_total_submission_limit(self):
        with self.assertRaises(exceptions.ValidationError) as cm:
            ag_models.Project.objects.validate_and_create(
                name='stove', course=self.course, total_submission_limit=0)

        self.assertIn('total_submission_limit', cm.exception.message_dict)

    def test_error_negative_total_submission_limit(self):
        with self.assertRaises(exceptions.ValidationError) as cm:
            ag_models.Project.objects.validate_and_create(
                name='stove', course=self.course, total_submission_limit=-1)

        self.assertIn('total_submission_limit', cm.exception.message_dict)

    def test_error_negative_num_bonus_submissions(self):
        with self.assertRaises(exceptions.ValidationError) as cm:
            ag_models.Project.objects.validate_and_create(
                name='merp', course=self.course, num_bonus_submissions=-1)

        self.assertIn('num_bonus_submissions', cm.exception.message_dict)

    def test_error_invalid_reset_timezone(self) -> None:
        with self.assertRaises(exceptions.ValidationError) as cm:
            ag_models.Project.objects.validate_and_create(
                name='merp', course=self.course, submission_limit_reset_timezone='nope')

        self.assertIn('submission_limit_reset_timezone', cm.exception.message_dict)


class ProjectNameExceptionTestCase(UnitTestBase):
    def setUp(self):
        super().setUp()

        self.course = obj_build.build_course()

    def test_exception_on_empty_name(self):
        with self.assertRaises(exceptions.ValidationError) as cm:
            ag_models.Project.objects.validate_and_create(
                name='', course=self.course)
        self.assertTrue('name' in cm.exception.message_dict)

    def test_exception_on_null_name(self):
        with self.assertRaises(exceptions.ValidationError) as cm:
            ag_models.Project.objects.validate_and_create(
                name=None, course=self.course)
        self.assertTrue('name' in cm.exception.message_dict)

    def test_exception_on_non_unique_name(self):
        name = 'project42'
        ag_models.Project.objects.validate_and_create(
            name=name, course=self.course)
        with self.assertRaises(exceptions.ValidationError):
            ag_models.Project.objects.validate_and_create(
                name=name, course=self.course)

    def test_no_exception_same_name_different_course(self):
        new_course = obj_build.build_course()
        name = 'project43'

        ag_models.Project.objects.validate_and_create(
            name=name, course=self.course)

        ag_models.Project.objects.validate_and_create(
            name=name, course=new_course)


class ProjectGroupSizeExceptionTestCase(UnitTestBase):
    def setUp(self):
        super().setUp()
        self.course = obj_build.build_course()
        self.project_name = 'project_for_group_tests'

    def test_exception_on_min_group_size_too_small(self):
        with self.assertRaises(exceptions.ValidationError) as cm:
            ag_models.Project.objects.validate_and_create(
                name=self.project_name, course=self.course,
                min_group_size=0)
        self.assertTrue('min_group_size' in cm.exception.message_dict)

    def test_exception_on_max_group_size_too_small(self):
        with self.assertRaises(exceptions.ValidationError) as cm:
            ag_models.Project.objects.validate_and_create(
                name=self.project_name, course=self.course,
                max_group_size=0)
        self.assertTrue('max_group_size' in cm.exception.message_dict)

    def test_exception_on_max_group_size_smaller_than_min_group_size(self):
        with self.assertRaises(exceptions.ValidationError) as cm:
            ag_models.Project.objects.validate_and_create(
                name=self.project_name, course=self.course,
                min_group_size=3, max_group_size=2)
        self.assertTrue('max_group_size' in cm.exception.message_dict)

    def test_exception_on_min_and_max_size_not_parseable_ints(self):
        with self.assertRaises(exceptions.ValidationError) as cm:
            ag_models.Project.objects.validate_and_create(
                name=self.project_name, course=self.course,
                min_group_size='spam', max_group_size='eggs')
        self.assertTrue('min_group_size' in cm.exception.message_dict)
        self.assertTrue('max_group_size' in cm.exception.message_dict)

    def test_no_exception_min_and_max_size_parseable_ints(self):
        ag_models.Project.objects.validate_and_create(
            name=self.project_name, course=self.course,
            min_group_size='1', max_group_size='2')

        loaded_project = ag_models.Project.objects.get(
            name=self.project_name, course=self.course)
        self.assertEqual(loaded_project.min_group_size, 1)
        self.assertEqual(loaded_project.max_group_size, 2)


class ProjectFilesystemTest(UnitTestBase):
    def setUp(self):
        super().setUp()

        self.course = obj_build.build_course()
        self.project_name = 'stats_project'

    def test_project_root_dir_created(self):
        project = ag_models.Project(name=self.project_name, course=self.course)

        self.assertEqual(
            [],
            os.listdir(os.path.dirname(core_ut.get_project_root_dir(project))))

        project.save()

        expected_project_root_dir = core_ut.get_project_root_dir(project)

        self.assertTrue(os.path.isdir(expected_project_root_dir))

    def test_project_files_dir_created(self):
        project = ag_models.Project(name=self.project_name, course=self.course)

        self.assertFalse(
            os.path.exists(
                os.path.dirname(core_ut.get_project_files_dir(project))))

        project.save()

        expected_project_files_dir = core_ut.get_project_files_dir(project)
        self.assertTrue(os.path.isdir(expected_project_files_dir))

    def test_project_submissions_dir_created(self):
        project = ag_models.Project(
            name=self.project_name, course=self.course)

        self.assertFalse(
            os.path.exists(
                os.path.dirname(
                    core_ut.get_project_groups_dir(project))))

        project.save()

        expected_project_submissions_by_student_dir = (
            core_ut.get_project_groups_dir(project))

        self.assertTrue(
            os.path.isdir(expected_project_submissions_by_student_dir))
