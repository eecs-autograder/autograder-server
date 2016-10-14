import random
import string

from autograder.utils.testing import UnitTestBase

import autograder.core.models as ag_models
import autograder.core.models.autograder_test_case.feedback_config as fdbk_lvls

import autograder.utils.testing.model_obj_builders as obj_build
from autograder.core.tests.test_models.test_autograder_test_case.models \
    import _DummyAutograderTestCase


class AgTestNameFdbkTestCase(UnitTestBase):
    def setUp(self):
        super().setUp()

        self.project = obj_build.build_project()
        self.ag_test_name = 'test case ' + random.choice(string.ascii_letters)
        self.ag_test = _DummyAutograderTestCase.objects.validate_and_create(
            name=self.ag_test_name,
            project=self.project)

        self.result = ag_models.AutograderTestCaseResult(
            test_case=self.ag_test)

    def test_randomly_obfuscated_name(self):
        self.ag_test.feedback_configuration.validate_and_update(
            ag_test_name_fdbk=(
                fdbk_lvls.AGTestNameFdbkLevel.randomly_obfuscate_name))

        generated_names = []
        for i in range(1000):
            name = self.result.get_normal_feedback().ag_test_name
            self.assertNotEqual(name, self.ag_test_name)
            self.assertTrue(name.startswith('test'))
            generated_names.append(name)

        self.assertCountEqual(set(generated_names), generated_names)

    def test_deterministically_obfuscate_name(self):
        self.ag_test.feedback_configuration.validate_and_update(
            ag_test_name_fdbk=(
                fdbk_lvls.AGTestNameFdbkLevel.deterministically_obfuscate_name)
        )

        self.ag_test.pk = random.randint(1, 1000)
        expected_name = 'test{}'.format(self.ag_test.pk)
        for i in range(100):
            self.assertEqual(expected_name,
                             self.result.get_normal_feedback().ag_test_name)

    def test_show_real_name(self):
        self.assertEqual(self.ag_test_name,
                         self.result.get_normal_feedback().ag_test_name)
