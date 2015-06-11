import datetime

from django.test import TestCase
from django.core.exceptions import ValidationError
from django.db.utils import IntegrityError

from autograder.models import Project, Semester, Course


class ProjectTestCase(TestCase):
    def setUp(self):
        self.course = Course.objects.create(name='eecs280')
        self.semester = Semester.objects.create(name='f15', course=self.course)
        self.PROJECT_NAME = 'stats_project'

    # -------------------------------------------------------------------------

    def test_valid_create_with_defaults(self):
        new_project = Project.objects.create(
            name=self.PROJECT_NAME, semester=self.semester)

        loaded_project = Project.get_by_composite_key(
            self.PROJECT_NAME, self.semester)

        self.assertEqual(loaded_project, new_project)
        self.assertEqual(loaded_project.name, new_project.name)
        self.assertEqual(loaded_project.semester, new_project.semester)

        self.assertEqual(loaded_project.project_files, [])
        self.assertEqual(loaded_project.visible_to_students, False)
        self.assertEqual(loaded_project.closing_time, None)
        self.assertEqual(loaded_project.disallow_student_submissions, False)
        self.assertEqual(loaded_project.min_group_size, 1)
        self.assertEqual(loaded_project.max_group_size, 1)
        self.assertEqual(loaded_project.required_student_files, [])
        self.assertEqual(loaded_project.expected_student_file_patterns, {})

    # -------------------------------------------------------------------------

    def test_valid_create_non_defaults(self):
        tomorrow_date = datetime.datetime.utcnow() + datetime.timedelta(days=1)
        min_group_size = 2
        max_group_size = 5
        required_student_files = ["spam.cpp", "eggs.cpp"]
        expected_student_file_patterns = {
            "test_*.cpp": [1, 10], "test[0-9].cpp": [2, 2]
        }

        new_project = Project.objects.create(
            name=self.PROJECT_NAME,
            semester=self.semester,
            visible_to_students=True,
            closing_time=tomorrow_date,
            disallow_student_submissions=True,
            min_group_size=min_group_size,
            max_group_size=max_group_size,
            required_student_files=required_student_files,
            expected_student_file_patterns=expected_student_file_patterns
        )

        loaded_project = Project.get_by_composite_key(
            self.PROJECT_NAME, self.semester)

        self.assertEqual(loaded_project, new_project)
        self.assertEqual(loaded_project.name, new_project.name)
        self.assertEqual(loaded_project.semester, new_project.semester)

        self.assertEqual(loaded_project.visible_to_students, True)
        self.assertEqual(loaded_project.closing_time, tomorrow_date)
        self.assertEqual(loaded_project.disallow_student_submissions, True)
        self.assertEqual(loaded_project.min_group_size, min_group_size)
        self.assertEqual(loaded_project.max_group_size, max_group_size)
        self.assertEqual(
            loaded_project.required_student_files, required_student_files)
        self.assertEqual(
            loaded_project.expected_student_file_patterns, expected_student_file_patterns)

    # -------------------------------------------------------------------------

    def test_exception_on_empty_name(self):
        with self.assertRaises(ValidationError):
            Project.objects.create(name='', semester=self.semester)

    # -------------------------------------------------------------------------

    def test_exception_on_null_name(self):
        with self.assertRaises(ValidationError):
            Project.objects.create(name=None, semester=self.semester)

    # -------------------------------------------------------------------------

    def test_exception_on_non_unique_name(self):
        Project.objects.create(name=self.PROJECT_NAME, semester=self.semester)
        with self.assertRaises(IntegrityError):
            Project.objects.create(
                name=self.PROJECT_NAME, semester=self.semester)

    # -------------------------------------------------------------------------

    def test_no_exception_same_name_different_semester(self):
        new_semester_name = 'w16'
        new_semester = Semester.objects.create(
            name=new_semester_name, course=self.course)

        Project.objects.create(name=self.PROJECT_NAME, semester=self.semester)
        new_project = Project.objects.create(
            name=self.PROJECT_NAME, semester=new_semester)

        loaded_new_project = Project.get_by_composite_key(
            self.PROJECT_NAME, new_semester)

        self.assertEqual(loaded_new_project, new_project)
        self.assertEqual(loaded_new_project.name, new_project.name)
        self.assertEqual(loaded_new_project.semester, new_project.semester)

    # -------------------------------------------------------------------------


