# from django.core import exceptions

# from .compiled_student_test_suite import CompiledStudentTestSuite


# class StudentTestSuiteFactory:
#     def new_instance(type_str, **kwargs):
#         return _get_class(type_str)(**kwargs)

#     def validate_and_create(type_str, **kwargs):
#         return _get_class(type_str).objects.validate_and_create(**kwargs)


# def _get_class(type_str):
#     try:
#         return _STR_TO_CLASS_MAPPINGS[type_str]
#     except KeyError:
#         raise exceptions.ValidationError(
#             "Invalid test suite type: '{}'".format(type_str))

# _STR_TO_CLASS_MAPPINGS = {
#     'compiled_student_test_suite': CompiledStudentTestSuite
# }
