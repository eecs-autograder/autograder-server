import datetime
import os
import random

from django.core import exceptions
from django.utils import timezone

import autograder.core.models as ag_models
import autograder.core.utils as core_ut

from autograder.utils.testing import UnitTestBase
import autograder.utils.testing.model_obj_builders as obj_build


class ProjectMiscTestCase(UnitTestBase):
    def setUp(self):
        super().setUp()

        self.course = obj_build.build_course()
        self.project_name = 'my_project'

    def test_valid_create_with_defaults(self):
        new_project = ag_models.Project.objects.validate_and_create(
            name=self.project_name, course=self.course)

        new_project.refresh_from_db()

        self.assertEqual(new_project, new_project)
        self.assertEqual(new_project.name, self.project_name)
        self.assertEqual(new_project.course, self.course)

        self.assertEqual(new_project.visible_to_students, False)
        self.assertEqual(new_project.closing_time, None)
        self.assertEqual(new_project.soft_closing_time, None)
        self.assertEqual(new_project.disallow_student_submissions, False)
        self.assertEqual(
            new_project.allow_submissions_from_non_enrolled_students,
            False)
        self.assertEqual(new_project.min_group_size, 1)
        self.assertEqual(new_project.max_group_size, 1)

        self.assertIsNone(new_project.submission_limit_per_day)
        self.assertEqual(True, new_project.allow_submissions_past_limit)
        self.assertEqual(datetime.time(),
                         new_project.submission_limit_reset_time)

        self.assertTrue(new_project.hide_ultimate_submission_fdbk)
        self.assertEqual(
            ag_models.Project.UltimateSubmissionSelectionMethod.most_recent,
            new_project.ultimate_submission_selection_method)

    def test_valid_create_non_defaults(self):
        tomorrow_date = timezone.now() + datetime.timedelta(days=1)
        soft_closing_time = tomorrow_date - timezone.timedelta(minutes=3)
        min_group_size = 2
        max_group_size = 5

        sub_limit = random.randint(1, 5)
        reset_time = datetime.time(8, 0, 0)

        selection_method = (ag_models.Project.UltimateSubmissionSelectionMethod
                                             .best_basic_score)

        new_project = ag_models.Project.objects.validate_and_create(
            name=self.project_name,
            course=self.course,
            visible_to_students=True,
            closing_time=tomorrow_date,
            soft_closing_time=soft_closing_time,
            disallow_student_submissions=True,
            allow_submissions_from_non_enrolled_students=True,
            min_group_size=min_group_size,
            max_group_size=max_group_size,

            submission_limit_per_day=sub_limit,
            allow_submissions_past_limit=False,
            submission_limit_reset_time=reset_time,

            hide_ultimate_submission_fdbk=False,
            ultimate_submission_selection_method=selection_method,
        )

        new_project.refresh_from_db()

        self.assertEqual(new_project, new_project)
        self.assertEqual(new_project.name, self.project_name)
        self.assertEqual(new_project.course, self.course)

        self.assertEqual(new_project.visible_to_students, True)
        self.assertEqual(new_project.closing_time, tomorrow_date)
        self.assertEqual(new_project.soft_closing_time, soft_closing_time)
        self.assertEqual(new_project.disallow_student_submissions, True)
        self.assertEqual(
            new_project.allow_submissions_from_non_enrolled_students,
            True)
        self.assertEqual(new_project.min_group_size, min_group_size)
        self.assertEqual(new_project.max_group_size, max_group_size)

        self.assertEqual(sub_limit, new_project.submission_limit_per_day)
        self.assertEqual(False, new_project.allow_submissions_past_limit)
        self.assertEqual(reset_time, new_project.submission_limit_reset_time)

        self.assertFalse(new_project.hide_ultimate_submission_fdbk)
        self.assertEqual(selection_method,
                         new_project.ultimate_submission_selection_method)

    def test_to_dict_default_fields(self):
        project = obj_build.build_project()

        expected_fields = [
            'name',
            'course',
            'visible_to_students',
            'closing_time',
            'soft_closing_time',
            'disallow_student_submissions',
            'allow_submissions_from_non_enrolled_students',
            'min_group_size',
            'max_group_size',

            'submission_limit_per_day',
            'allow_submissions_past_limit',
            'submission_limit_reset_time',

            'ultimate_submission_selection_method',
            'hide_ultimate_submission_fdbk',
        ]

        self.assertCountEqual(expected_fields,
                              ag_models.Project.get_default_to_dict_fields())
        project = obj_build.build_project()
        self.assertTrue(project.to_dict())

    def test_editable_fields(self):
        expected = [
            'name',
            'visible_to_students',
            'closing_time',
            'soft_closing_time',
            'disallow_student_submissions',
            'allow_submissions_from_non_enrolled_students',
            'min_group_size',
            'max_group_size',

            'submission_limit_per_day',
            'allow_submissions_past_limit',
            'submission_limit_reset_time',

            'ultimate_submission_selection_method',
            'hide_ultimate_submission_fdbk',
        ]
        self.assertCountEqual(expected,
                              ag_models.Project.get_editable_fields())


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
        self.assertEqual(closing_time, proj.closing_time)
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

    def test_error_invalid_ultimate_submission_selection_method(self):
        with self.assertRaises(exceptions.ValidationError) as cm:
            ag_models.Project.objects.validate_and_create(
                name='steve', course=self.course,
                ultimate_submission_selection_method='not_a_method')

        self.assertIn('ultimate_submission_selection_method',
                      cm.exception.message_dict)


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
        project = ag_models.Project(
            name=self.project_name, course=self.course)

        self.assertEqual(
            [],
            os.listdir(os.path.dirname(core_ut.get_project_root_dir(project))))

        project.save()

        expected_project_root_dir = core_ut.get_project_root_dir(project)

        self.assertTrue(os.path.isdir(expected_project_root_dir))

    def test_project_files_dir_created(self):
        project = ag_models.Project(
            name=self.project_name, course=self.course)

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
                    core_ut.get_project_submission_groups_dir(project))))

        project.save()

        expected_project_submissions_by_student_dir = (
            core_ut.get_project_submission_groups_dir(project))

        self.assertTrue(
            os.path.isdir(expected_project_submissions_by_student_dir))
