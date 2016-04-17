import os
import datetime

from django.core import exceptions
from django.utils import timezone

import autograder.core.models as ag_models

import autograder.core.shared.utilities as ut

from autograder.core.tests.temporary_filesystem_test_case import (
    TemporaryFilesystemTestCase)
import autograder.core.tests.dummy_object_utils as obj_ut


class ProjectMiscTestCase(TemporaryFilesystemTestCase):
    def setUp(self):
        super().setUp()

        self.semester = obj_ut.build_semester()
        self.project_name = 'my_project'

    def test_valid_create_with_defaults(self):
        new_project = ag_models.Project.objects.validate_and_create(
            name=self.project_name, semester=self.semester)

        new_project.refresh_from_db()

        self.assertEqual(new_project, new_project)
        self.assertEqual(new_project.name, self.project_name)
        self.assertEqual(new_project.semester, self.semester)

        self.assertEqual(new_project.visible_to_students, False)
        self.assertEqual(new_project.closing_time, None)
        self.assertEqual(new_project.disallow_student_submissions, False)
        self.assertEqual(
            new_project.allow_submissions_from_non_enrolled_students,
            False)
        self.assertEqual(new_project.min_group_size, 1)
        self.assertEqual(new_project.max_group_size, 1)

    def test_valid_create_non_defaults(self):
        tomorrow_date = timezone.now() + datetime.timedelta(days=1)
        min_group_size = 2
        max_group_size = 5

        new_project = ag_models.Project.objects.validate_and_create(
            name=self.project_name,
            semester=self.semester,
            visible_to_students=True,
            closing_time=tomorrow_date,
            disallow_student_submissions=True,
            allow_submissions_from_non_enrolled_students=True,
            min_group_size=min_group_size,
            max_group_size=max_group_size,
        )

        new_project.refresh_from_db()

        self.assertEqual(new_project, new_project)
        self.assertEqual(new_project.name, self.project_name)
        self.assertEqual(new_project.semester, self.semester)

        self.assertEqual(new_project.visible_to_students, True)
        self.assertEqual(new_project.closing_time, tomorrow_date)
        self.assertEqual(new_project.disallow_student_submissions, True)
        self.assertEqual(
            new_project.allow_submissions_from_non_enrolled_students,
            True)
        self.assertEqual(new_project.min_group_size, min_group_size)
        self.assertEqual(new_project.max_group_size, max_group_size)

    def test_to_dict_default_fields(self):
        project = obj_ut.build_project()

        expected_fields = [
            'name',
            'semester',
            'visible_to_students',
            'closing_time',
            'disallow_student_submissions',
            'allow_submissions_from_non_enrolled_students',
            'min_group_size',
            'max_group_size',
        ]

        self.assertCountEqual(expected_fields,
                              project.DEFAULT_INCLUDE_FIELDS)


class ProjectNameExceptionTestCase(TemporaryFilesystemTestCase):
    def setUp(self):
        super().setUp()

        self.semester = obj_ut.build_semester()

    def test_exception_on_empty_name(self):
        with self.assertRaises(exceptions.ValidationError) as cm:
            ag_models.Project.objects.validate_and_create(
                name='', semester=self.semester)
        self.assertTrue('name' in cm.exception.message_dict)

    def test_exception_on_null_name(self):
        with self.assertRaises(exceptions.ValidationError) as cm:
            ag_models.Project.objects.validate_and_create(
                name=None, semester=self.semester)
        self.assertTrue('name' in cm.exception.message_dict)

    def test_exception_on_non_unique_name(self):
        name = 'project42'
        ag_models.Project.objects.validate_and_create(
            name=name, semester=self.semester)
        with self.assertRaises(exceptions.ValidationError):
            ag_models.Project.objects.validate_and_create(
                name=name, semester=self.semester)

    def test_no_exception_same_name_different_semester(self):
        new_semester = obj_ut.build_semester()
        name = 'project43'

        ag_models.Project.objects.validate_and_create(
            name=name, semester=self.semester)

        ag_models.Project.objects.validate_and_create(
            name=name, semester=new_semester)


class ProjectGroupSizeExceptionTestCase(TemporaryFilesystemTestCase):
    def setUp(self):
        super().setUp()
        self.semester = obj_ut.build_semester()
        self.project_name = 'project_for_group_tests'

    def test_exception_on_min_group_size_too_small(self):
        with self.assertRaises(exceptions.ValidationError) as cm:
            ag_models.Project.objects.validate_and_create(
                name=self.project_name, semester=self.semester,
                min_group_size=0)
        self.assertTrue('min_group_size' in cm.exception.message_dict)

    def test_exception_on_max_group_size_too_small(self):
        with self.assertRaises(exceptions.ValidationError) as cm:
            ag_models.Project.objects.validate_and_create(
                name=self.project_name, semester=self.semester,
                max_group_size=0)
        self.assertTrue('max_group_size' in cm.exception.message_dict)

    def test_exception_on_max_group_size_smaller_than_min_group_size(self):
        with self.assertRaises(exceptions.ValidationError) as cm:
            ag_models.Project.objects.validate_and_create(
                name=self.project_name, semester=self.semester,
                min_group_size=3, max_group_size=2)
        self.assertTrue('max_group_size' in cm.exception.message_dict)

    def test_exception_on_min_and_max_size_not_parseable_ints(self):
        with self.assertRaises(exceptions.ValidationError) as cm:
            ag_models.Project.objects.validate_and_create(
                name=self.project_name, semester=self.semester,
                min_group_size='spam', max_group_size='eggs')
        self.assertTrue('min_group_size' in cm.exception.message_dict)
        self.assertTrue('max_group_size' in cm.exception.message_dict)

    def test_no_exception_min_and_max_size_parseable_ints(self):
        ag_models.Project.objects.validate_and_create(
            name=self.project_name, semester=self.semester,
            min_group_size='1', max_group_size='2')

        loaded_project = ag_models.Project.objects.get(
            name=self.project_name, semester=self.semester)
        self.assertEqual(loaded_project.min_group_size, 1)
        self.assertEqual(loaded_project.max_group_size, 2)


class ProjectFilesystemTest(TemporaryFilesystemTestCase):
    def setUp(self):
        super().setUp()

        self.semester = obj_ut.build_semester()
        self.project_name = 'stats_project'

    def test_project_root_dir_created(self):
        project = ag_models.Project(
            name=self.project_name, semester=self.semester)

        self.assertEqual(
            [],
            os.listdir(os.path.dirname(ut.get_project_root_dir(project))))

        project.save()

        expected_project_root_dir = ut.get_project_root_dir(project)

        self.assertTrue(os.path.isdir(expected_project_root_dir))

    def test_project_files_dir_created(self):
        project = ag_models.Project(
            name=self.project_name, semester=self.semester)

        self.assertFalse(
            os.path.exists(
                os.path.dirname(ut.get_project_files_dir(project))))

        project.save()

        expected_project_files_dir = ut.get_project_files_dir(project)
        self.assertTrue(os.path.isdir(expected_project_files_dir))

    def test_project_submissions_dir_created(self):
        project = ag_models.Project(
            name=self.project_name, semester=self.semester)

        self.assertFalse(
            os.path.exists(
                os.path.dirname(
                    ut.get_project_submission_groups_dir(project))))

        project.save()

        expected_project_submissions_by_student_dir = (
            ut.get_project_submission_groups_dir(project))

        self.assertTrue(
            os.path.isdir(expected_project_submissions_by_student_dir))
