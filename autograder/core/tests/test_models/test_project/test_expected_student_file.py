import random

from django.core import exceptions

import autograder.utils.testing.model_obj_builders as obj_build
from autograder.core.models.project.expected_student_file import (
    ExpectedStudentFile)
from autograder.utils.testing import UnitTestBase


class ExpectedStudentFileTestCase(UnitTestBase):
    def setUp(self):
        super().setUp()
        self.project = obj_build.build_project()

        self.valid_pattern = 'test_[0-4][!a-z]?.*.cpp'

    def test_serializable_fields(self):
        expected = [
            'pk',
            'project',
            'pattern',
            'min_num_matches',
            'max_num_matches'
        ]

        self.assertCountEqual(
            expected,
            ExpectedStudentFile.get_serializable_fields())

        pattern = ExpectedStudentFile.objects.validate_and_create(
            project=self.project,
            pattern=self.valid_pattern)

        self.assertTrue(pattern.to_dict())

    def test_editable_fields(self):
        expected = [
            'pattern',
            'min_num_matches',
            'max_num_matches'
        ]
        self.assertCountEqual(expected,
                              ExpectedStudentFile.get_editable_fields())

    def test_valid_create_defaults(self):
        student_file = ExpectedStudentFile.objects.validate_and_create(
            project=self.project,
            pattern=self.valid_pattern)

        student_file.refresh_from_db()

        self.assertEqual(self.project, student_file.project)
        self.assertEqual(self.valid_pattern, student_file.pattern)
        self.assertEqual(1, student_file.min_num_matches)
        self.assertEqual(1, student_file.max_num_matches)

    def test_valid_create_no_defaults(self):
        min_matches = random.randint(0, 2)
        max_matches = min_matches + random.randint(0, 2)
        student_file = ExpectedStudentFile.objects.validate_and_create(
            project=self.project,
            pattern=self.valid_pattern,
            min_num_matches=min_matches,
            max_num_matches=max_matches
        )

        student_file.refresh_from_db()

        self.assertEqual(self.project, student_file.project)
        self.assertEqual(self.valid_pattern, student_file.pattern)
        self.assertEqual(min_matches, student_file.min_num_matches)
        self.assertEqual(max_matches, student_file.max_num_matches)

    def test_exception_pattern_exists(self):
        ExpectedStudentFile.objects.validate_and_create(
            project=self.project,
            pattern=self.valid_pattern,
            min_num_matches=1,
            max_num_matches=2)

        with self.assertRaises(exceptions.ValidationError):
            ExpectedStudentFile.objects.validate_and_create(
                project=self.project,
                pattern=self.valid_pattern,
                min_num_matches=1,
                max_num_matches=2)

    def test_no_exception_same_pattern_as_other_project(self):
        ExpectedStudentFile.objects.validate_and_create(
            project=self.project,
            pattern=self.valid_pattern,
            min_num_matches=1,
            max_num_matches=2)

        other_project = obj_build.build_project()
        ExpectedStudentFile.objects.validate_and_create(
            project=other_project,
            pattern=self.valid_pattern,
            min_num_matches=1,
            max_num_matches=2)

    def test_exception_negative_min_matches(self):
        with self.assertRaises(exceptions.ValidationError) as cm:
            ExpectedStudentFile.objects.validate_and_create(
                project=self.project,
                pattern=self.valid_pattern,
                min_num_matches=-1,
                max_num_matches=2)

        self.assertIn('min_num_matches', cm.exception.message_dict)

    def test_exception_max_matches_less_than_min(self):
        min_matches = random.randint(1, 4)
        with self.assertRaises(exceptions.ValidationError) as cm:
            ExpectedStudentFile.objects.validate_and_create(
                project=self.project,
                pattern=self.valid_pattern,
                min_num_matches=min_matches,
                max_num_matches=min_matches - 1)

        self.assertIn('max_num_matches', cm.exception.message_dict)

    def test_exception_illegal_patterns(self):
        illegal_patterns = [
            '..',
            '../../../hack/you/now',
            '/usr/bin/haxorz',
            '',
        ]

        for pattern in illegal_patterns:
            with self.assertRaises(exceptions.ValidationError,
                                   msg="Pattern: " + pattern) as cm:
                ExpectedStudentFile.objects.validate_and_create(
                    project=self.project,
                    pattern=pattern,
                    min_num_matches=1,
                    max_num_matches=2)

            self.assertIn('pattern', cm.exception.message_dict)
