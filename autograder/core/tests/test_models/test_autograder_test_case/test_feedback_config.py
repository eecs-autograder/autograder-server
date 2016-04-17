import random

from django.core import exceptions

import autograder.core.models as ag_models
import autograder.core.models.autograder_test_case.feedback_config as fdbk_lvls

from .models import _DummyAutograderTestCase
import autograder.core.tests.dummy_object_utils as obj_ut
from autograder.core.tests.temporary_filesystem_test_case import (
    TemporaryFilesystemTestCase)


class AutograderFeedbackConfigurationTestCase(TemporaryFilesystemTestCase):
    def setUp(self):
        super().setUp()

    def test_valid_create_with_defaults(self):
        fdbk_conf = ag_models.FeedbackConfig.objects.validate_and_create()

        fdbk_conf.refresh_from_db()

        self.assertEqual(fdbk_lvls.AGTestNameFdbkLevel.show_real_name,
                         fdbk_conf.ag_test_name_fdbk)
        self.assertEqual(fdbk_lvls.ReturnCodeFdbkLevel.no_feedback,
                         fdbk_conf.return_code_fdbk)
        self.assertEqual(fdbk_lvls.StdoutFdbkLevel.no_feedback,
                         fdbk_conf.stdout_fdbk)
        self.assertEqual(fdbk_lvls.StderrFdbkLevel.no_feedback,
                         fdbk_conf.stderr_fdbk)
        self.assertEqual(fdbk_lvls.CompilationFdbkLevel.no_feedback,
                         fdbk_conf.compilation_fdbk)
        self.assertEqual(fdbk_lvls.ValgrindFdbkLevel.no_feedback,
                         fdbk_conf.valgrind_fdbk)
        self.assertEqual(fdbk_lvls.PointsFdbkLevel.hide,
                         fdbk_conf.points_fdbk)

    def test_valid_create_no_defaults(self):
        for i in range(20):
            vals = {
                'ag_test_name_fdbk': random.choice(
                    fdbk_lvls.AGTestNameFdbkLevel.values),
                'return_code_fdbk': random.choice(
                    fdbk_lvls.ReturnCodeFdbkLevel.values),
                'stdout_fdbk': random.choice(
                    fdbk_lvls.StdoutFdbkLevel.values),
                'stderr_fdbk': random.choice(
                    fdbk_lvls.StderrFdbkLevel.values),
                'compilation_fdbk': random.choice(
                    fdbk_lvls.CompilationFdbkLevel.values),
                'valgrind_fdbk': random.choice(
                    fdbk_lvls.ValgrindFdbkLevel.values),
                'points_fdbk': random.choice(
                    fdbk_lvls.PointsFdbkLevel.values),
            }

            fdbk_conf = ag_models.FeedbackConfig.objects.validate_and_create(
                **vals)

            fdbk_conf.refresh_from_db()

            for key, value in vals.items():
                self.assertEqual(value, getattr(fdbk_conf, key),
                                 msg='Field: ' + key)

            fdbk_conf.delete()

    def test_exception_invalid_values(self):
        with self.assertRaises(exceptions.ValidationError) as cm:
            ag_models.FeedbackConfig.objects.validate_and_create(
                ag_test_name_fdbk='not_a_value',
                return_code_fdbk='not_a_value',
                stdout_fdbk='not_a_value',
                stderr_fdbk='not_a_value',
                compilation_fdbk='not_a_value',
                valgrind_fdbk='not_a_value',
                points_fdbk='not_a_value')

        self.assertIn('ag_test_name_fdbk', cm.exception.message_dict)
        self.assertIn('return_code_fdbk', cm.exception.message_dict)
        self.assertIn('stdout_fdbk', cm.exception.message_dict)
        self.assertIn('stderr_fdbk', cm.exception.message_dict)
        self.assertIn('compilation_fdbk', cm.exception.message_dict)
        self.assertIn('valgrind_fdbk', cm.exception.message_dict)
        self.assertIn('points_fdbk', cm.exception.message_dict)

    def test_to_dict_default_fields(self):
        field_names = [
            'ag_test_name_fdbk',
            'return_code_fdbk',
            'stdout_fdbk',
            'stderr_fdbk',
            'compilation_fdbk',
            'valgrind_fdbk',
            'points_fdbk',
        ]

        self.assertCountEqual(
            field_names, ag_models.FeedbackConfig.DEFAULT_INCLUDE_FIELDS)
