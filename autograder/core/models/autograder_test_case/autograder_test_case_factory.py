from django.core import exceptions

from .compiled_autograder_test_case import CompiledAndRunAutograderTestCase
from .compiled_autograder_test_case import CompilationOnlyAutograderTestCase
from .interpreted_autograder_test_case import InterpretedAutograderTestCase


class AutograderTestCaseFactory(object):
    def new_instance(type_str, **kwargs):
        return _get_class(type_str)(**kwargs)

    def validate_and_create(type_str, **kwargs):
        return _get_class(type_str).objects.validate_and_create(**kwargs)


def _get_class(type_str):
    try:
        return _STR_TO_CLASS_MAPPINGS[type_str]
    except KeyError:
        raise exceptions.ValidationError(
            {'type_str': "Invalid test case type: '{}'".format(type_str)})

_STR_TO_CLASS_MAPPINGS = {
    'compiled_and_run_test_case': CompiledAndRunAutograderTestCase,
    'compilation_only_test_case': CompilationOnlyAutograderTestCase,
    'interpreted_test_case': InterpretedAutograderTestCase,
}
