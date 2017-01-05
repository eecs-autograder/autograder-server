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

        self.assertFalse(new_project.visible_to_students)
        self.assertIsNone(new_project.closing_time)
        self.assertIsNone(new_project.soft_closing_time)
        self.assertFalse(new_project.disallow_student_submissions)
        self.assertFalse(new_project.disallow_group_registration)
        self.assertFalse(new_project.allow_submissions_from_non_enrolled_students)
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
        kwargs = {
            'name': self.project_name,
            'course': self.course,
            'visible_to_students': True,
            'closing_time': tomorrow_date,
            'soft_closing_time': soft_closing_time,
            'disallow_student_submissions': True,
            'disallow_group_registration': True,
            'allow_submissions_from_non_enrolled_students': True,
            'min_group_size': min_group_size,
            'max_group_size': max_group_size,

            'submission_limit_per_day': sub_limit,
            'allow_submissions_past_limit': False,
            'submission_limit_reset_time': reset_time,

            'hide_ultimate_submission_fdbk': False,
            'ultimate_submission_selection_method': selection_method,
        }

        new_project = ag_models.Project.objects.validate_and_create(
            **kwargs
        )

        new_project.refresh_from_db()

        for field_name, value in kwargs.items():
            self.assertEqual(value, getattr(new_project, field_name),
                             msg=field_name)

    def test_serializable_fields(self):
        project = obj_build.build_project()

        expected_fields = [
            'pk',
            'name',
            'course',
            'visible_to_students',
            'closing_time',
            'soft_closing_time',
            'disallow_student_submissions',
            'disallow_group_registration',
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
                              ag_models.Project.get_serializable_fields())
        project = obj_build.build_project()
        self.assertTrue(project.to_dict())

    def test_editable_fields(self):
        expected = [
            'name',
            'visible_to_students',
            'closing_time',
            'soft_closing_time',
            'disallow_student_submissions',
            'disallow_group_registration',
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


class CloneProjectTestCase(UnitTestBase):
    def test_empty_relationships(self):
        proj = obj_build.build_project(
            {'disallow_student_submissions': True,
            'disallow_group_registration': True,
            'allow_submissions_from_non_enrolled_students': True,
            'min_group_size': 2,
            'max_group_size': 5,})
        test_case = obj_build.build_compiled_ag_test(proj)
        self.do_clone_project_test(proj)

    def test_all_relationships(self):
        self.fail()

    def test_duplicate_patterns_in_different_projects(self):
        self.fail()

    def test_duplicate_file_objs_in_different_projects(self):
        self.fail()

    def do_clone_project_test(self, project):
        # compare properties
        cloned = project.clone()
        cloned_dict = cloned.to_dict(exclude_fields=['pk'])
        project_dict = project.to_dict(exclude_fields=['pk'])
        self.assertEqual(cloned_dict, project_dict)
        self.assertNotEqual(cloned, project)

        exclude_fields = ['pk', 'project']
        self.check_project_relationship("uploaded_files",
                                        orig_proj=project,
                                        clone_proj=cloned,
                                        exclude_fields=exclude_fields)
        self.check_project_relationship("expected_student_file_patterns",
                                        orig_proj=project,
                                        clone_proj=cloned,
                                        exclude_fields=exclude_fields)

        ag_test_exclude_fields = (
            exclude_fields +
            ag_models.AutograderTestCaseBase.RELATED_FILE_FIELD_NAMES
        )

        self.check_project_relationship("autograder_test_cases",
                                        orig_proj=project,
                                        clone_proj=cloned,
                                        exclude_fields=ag_test_exclude_fields)

        self.check_ag_test_relationships(orig_proj=project, clone_proj=cloned)

    def check_project_relationship(self, relationship_name, orig_proj,
                                   clone_proj, exclude_fields):
        cloned_objs = getattr(clone_proj, relationship_name).all()
        orig_objs = getattr(orig_proj, relationship_name).all()

        self.assertEqual(cloned_objs.count(), orig_objs.count())

        for cloned_obj, orig_obj in zip(cloned_objs, orig_objs):
            cloned_obj_dict = cloned_obj.to_dict(exclude_fields=exclude_fields)
            orig_obj_dict = orig_obj.to_dict(exclude_fields=exclude_fields)
            self.assertEqual(cloned_obj_dict, orig_obj_dict)
            self.assertNotEqual(cloned_obj.pk, orig_obj.pk)
            self.assertNotEqual(cloned_obj.project, orig_obj.project)

    def check_ag_test_relationships(self, orig_proj, clone_proj):
        exclude_fields = ['pk', 'project']
        cloned_tests = clone_proj.autograder_test_cases.all()
        proj_tests = orig_proj.autograder_test_cases.all()

        for cloned_test, proj_test in zip(cloned_tests, proj_tests):
            cloned_related_fields_dict = cloned_test.to_dict(
                include_fields=ag_models.AutograderTestCaseBase.RELATED_FILE_FIELD_NAMES)
            project_related_fields_dict = proj_test.to_dict(
                include_fields=ag_models.AutograderTestCaseBase.RELATED_FILE_FIELD_NAMES)

            for key, value in cloned_related_fields_dict.items():
                self.assertNotEqual(set(project_related_fields_dict[key]), set(value))

                cloned_test_dicts = [
                    getattr(cloned_test, key).get(pk=pk).to_dict(
                        exclude_fields=exclude_fields) for pk in value
                ]

                project_test_dicts = [
                    getattr(proj_test, key).get(pk=pk).to_dict(
                        exclude_fields=exclude_fields)
                    for pk in project_related_fields_dict[key]
                ]

                self.assertCountEqual(cloned_test_dicts, project_test_dicts)
