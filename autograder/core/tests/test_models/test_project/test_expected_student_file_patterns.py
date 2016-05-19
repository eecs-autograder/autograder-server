import random

from django.core import exceptions

from autograder.core.models.project.expected_student_file_pattern import (
    ExpectedStudentFilePattern)

from autograder.core.tests.temporary_filesystem_test_case import (
    TemporaryFilesystemTestCase)
import autograder.core.tests.dummy_object_utils as obj_ut


class CreateExpectedStudentFilePatternTestCase(TemporaryFilesystemTestCase):
    def setUp(self):
        super().setUp()
        self.project = obj_ut.build_project()

        self.valid_pattern = 'test_[0-4][!a-z]?.*.cpp'

    def test_default_to_dict_fields(self):
        expected = [
            'project',
            'pattern',
            'min_num_matches',
            'max_num_matches'
        ]

        self.assertCountEqual(
            expected,
            ExpectedStudentFilePattern.get_default_to_dict_fields())

        pattern = ExpectedStudentFilePattern.objects.validate_and_create(
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
                              ExpectedStudentFilePattern.get_editable_fields())

    def test_valid_create_defaults(self):
        pattern = ExpectedStudentFilePattern.objects.validate_and_create(
            project=self.project,
            pattern=self.valid_pattern)

        pattern.refresh_from_db()

        self.assertEqual(self.project, pattern.project)
        self.assertEqual(self.valid_pattern, pattern.pattern)
        self.assertEqual(1, pattern.min_num_matches)
        self.assertEqual(1, pattern.max_num_matches)

    def test_valid_create_no_defaults(self):
        min_matches = random.randint(0, 2)
        max_matches = min_matches + random.randint(0, 2)
        pattern = ExpectedStudentFilePattern.objects.validate_and_create(
            project=self.project,
            pattern=self.valid_pattern,
            min_num_matches=min_matches,
            max_num_matches=max_matches
        )

        pattern.refresh_from_db()

        self.assertEqual(self.project, pattern.project)
        self.assertEqual(self.valid_pattern, pattern.pattern)
        self.assertEqual(min_matches, pattern.min_num_matches)
        self.assertEqual(max_matches, pattern.max_num_matches)

    def test_exception_pattern_exists(self):
        ExpectedStudentFilePattern.objects.validate_and_create(
            project=self.project,
            pattern=self.valid_pattern,
            min_num_matches=1,
            max_num_matches=2)

        with self.assertRaises(exceptions.ValidationError):
            ExpectedStudentFilePattern.objects.validate_and_create(
                project=self.project,
                pattern=self.valid_pattern,
                min_num_matches=1,
                max_num_matches=2)

    def test_no_exception_same_pattern_as_other_project(self):
        ExpectedStudentFilePattern.objects.validate_and_create(
            project=self.project,
            pattern=self.valid_pattern,
            min_num_matches=1,
            max_num_matches=2)

        other_project = obj_ut.build_project()
        ExpectedStudentFilePattern.objects.validate_and_create(
            project=other_project,
            pattern=self.valid_pattern,
            min_num_matches=1,
            max_num_matches=2)

    def test_exception_negative_min_matches(self):
        with self.assertRaises(exceptions.ValidationError) as cm:
            ExpectedStudentFilePattern.objects.validate_and_create(
                project=self.project,
                pattern=self.valid_pattern,
                min_num_matches=-1,
                max_num_matches=2)

        self.assertIn('min_num_matches', cm.exception.message_dict)

    def test_exception_max_matches_less_than_min(self):
        min_matches = random.randint(1, 4)
        with self.assertRaises(exceptions.ValidationError) as cm:
            ExpectedStudentFilePattern.objects.validate_and_create(
                project=self.project,
                pattern=self.valid_pattern,
                min_num_matches=min_matches,
                max_num_matches=min_matches - 1)

        self.assertIn('max_num_matches', cm.exception.message_dict)

    def test_exception_illegal_patterns(self):
        illegal_patterns = [
            'test_*.; echo "haxorz";#',
            '../../../hack/you/now',
            '/usr/bin/haxorz',
            '',
            '    '
        ]

        for pattern in illegal_patterns:
            with self.assertRaises(exceptions.ValidationError,
                                   msg="Pattern: " + pattern) as cm:
                ExpectedStudentFilePattern.objects.validate_and_create(
                    project=self.project,
                    pattern=pattern,
                    min_num_matches=1,
                    max_num_matches=2)

            self.assertIn('pattern', cm.exception.message_dict)
