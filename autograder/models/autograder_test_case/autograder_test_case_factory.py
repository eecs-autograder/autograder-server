from .compiled_autograder_test_case import CompiledAutograderTestCase


class AutograderTestCaseFactory(object):
    def new_instance(type_str, **kwargs):
        if type_str == 'compiled_test_case':
            return CompiledAutograderTestCase(**kwargs)
        raise ValueError("Invalid test case type: '{}'".format(type_str))

    def validate_and_create(type_str, **kwargs):
        if type_str == 'compiled_test_case':
            return CompiledAutograderTestCase.objects.validate_and_create(
                **kwargs)

        raise ValueError("Invalid test case type: '{}'".format(type_str))
