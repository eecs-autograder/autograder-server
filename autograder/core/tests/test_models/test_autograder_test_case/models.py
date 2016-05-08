from autograder.core.models import (
    AutograderTestCaseBase, CompiledAutograderTestCase)

# -----------------------------------------------------------------------------
# DUMMY MODELS FOR TESTING AUTOGRADER TEST CASE HIERARCHY
# -----------------------------------------------------------------------------


class _DummyAutograderTestCase(AutograderTestCaseBase):
    class Meta:
        proxy = True

    @property
    def type_str(self):
        return 'dummy'


class _DummyCompiledAutograderTestCase(CompiledAutograderTestCase):
    class Meta:
        proxy = True
