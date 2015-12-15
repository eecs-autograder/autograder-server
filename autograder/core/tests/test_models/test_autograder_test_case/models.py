from autograder.core.models import (
    AutograderTestCaseBase, CompiledAutograderTestCase)

# -----------------------------------------------------------------------------
# DUMMY MODELS FOR TESTING AUTOGRADER TEST CASE HIERARCHY
# -----------------------------------------------------------------------------


class _DummyAutograderTestCase(AutograderTestCaseBase):
    pass


class _DummyCompiledAutograderTestCase(CompiledAutograderTestCase):
    pass
