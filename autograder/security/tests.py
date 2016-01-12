from django.test import TestCase


class AutograderSandboxTestCase(TestCase):
    import unittest
    @unittest.skip('todo')
    def test_sandbox_default_init(self):
        self.fail()

    @unittest.skip('todo')
    def test_sandbox_networking_enabled(self):
        self.fail()

    @unittest.skip('todo')
    def test_sandbox_networking_disabled(self):
        self.fail()

    @unittest.skip('todo')
    def test_sandbox_environment_variables_set(self):
        self.fail()
