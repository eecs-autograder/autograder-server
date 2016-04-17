# import datetime

# from django.core.files.uploadedfile import SimpleUploadedFile
# from django.utils import timezone
# from autograder.core.tests.temporary_filesystem_test_case import (
#     TemporaryFilesystemTestCase)

# import autograder.core.tests.dummy_object_utils as obj_ut

# from autograder.core.models import (
#     StudentTestSuiteFactory, SubmissionGroup, Submission, Project,
#     StudentTestSuiteResult)

# import autograder.core.shared.feedback_configuration as fbc


# class _SharedSetUp(TemporaryFilesystemTestCase):
#     def setUp(self):
#         super().setUp()

#         self.maxDiff = None

#         self.group = obj_ut.build_submission_group(
#             project_kwargs={
#                 'expected_student_file_patterns': [
#                     Project.FilePatternTuple('test_*.cpp', 1, 3)
#                 ],
#                 'allow_submissions_from_non_enrolled_students': True,
#                 'closing_time': timezone.now() + datetime.timedelta(hours=-1)
#             }
#         )
#         self.project = self.group.project

#         proj_files = [
#             SimpleUploadedFile('correct.cpp', b'blah'),
#             SimpleUploadedFile('buggy1.cpp', b'buuug'),
#             SimpleUploadedFile('buggy2.cpp', b'buuug')
#         ]
#         for file_ in proj_files:
#             self.project.add_project_file(file_)

#         self.suite = StudentTestSuiteFactory.validate_and_create(
#             'compiled_student_test_suite',
#             name='suite',
#             project=self.project,
#             student_test_case_filename_pattern='test_*.cpp',
#             correct_implementation_filename='correct.cpp',
#             buggy_implementation_filenames=['buggy1.cpp', 'buggy2.cpp'],
#             points_per_buggy_implementation_exposed=2,
#             compiler='g++',
#         )

#         submitted_files = [
#             SimpleUploadedFile('test_1.cpp', b'asdf'),
#             SimpleUploadedFile('test_2.cpp', b'asdf'),
#             SimpleUploadedFile('test_expose_none.cpp', b'asdf'),
#             SimpleUploadedFile('test_no_compile.cpp', b'asdf'),
#             SimpleUploadedFile('test_invalid.cpp', b'asdf'),
#             SimpleUploadedFile('test_timeout.cpp', b'asdf')
#         ]
#         self.submission = Submission.objects.validate_and_create(
#             submission_group=self.group,
#             submitted_files=submitted_files)

#         self.detailed_suite_results = [
#             StudentTestSuiteResult.new_test_evaluation_result_instance(
#                 'test_1.cpp',
#                 compilation_return_code=0,
#                 compilation_standard_output='asdkljf;adjf',
#                 compilation_standard_error_output='amdsnf;s',
#                 valid=True,
#                 validity_check_standard_output='askdjf',
#                 validity_check_standard_error_output='ajdsnf',
#                 timed_out=False,
#                 buggy_implementations_exposed=['buggy1.cpp'],
#             ),
#             StudentTestSuiteResult.new_test_evaluation_result_instance(
#                 'test_2.cpp',
#                 compilation_return_code=0,
#                 compilation_standard_output='asdkljf;adjf',
#                 compilation_standard_error_output='amdsnf;s',
#                 valid=True,
#                 validity_check_standard_output='askdjf',
#                 validity_check_standard_error_output='ajdsnf',
#                 timed_out=False,
#                 buggy_implementations_exposed=['buggy2.cpp'],
#             ),
#             StudentTestSuiteResult.new_test_evaluation_result_instance(
#                 'test_expose_none.cpp',
#                 compilation_return_code=0,
#                 compilation_standard_output='asdkljf;adjf',
#                 compilation_standard_error_output='amdsnf;s',
#                 valid=True,
#                 validity_check_standard_output='askdjf',
#                 validity_check_standard_error_output='ajdsnf',
#                 timed_out=False,
#                 buggy_implementations_exposed=[],
#             ),
#             StudentTestSuiteResult.new_test_evaluation_result_instance(
#                 'test_no_compile.cpp',
#                 compilation_return_code=42,
#                 compilation_standard_output='asdkljf;adjf',
#                 compilation_standard_error_output='amdsnf;s',
#                 valid=None,
#                 validity_check_standard_output=None,
#                 validity_check_standard_error_output=None,
#                 timed_out=None,
#                 buggy_implementations_exposed=[],
#             ),
#             StudentTestSuiteResult.new_test_evaluation_result_instance(
#                 'test_invalid.cpp',
#                 compilation_return_code=0,
#                 compilation_standard_output='asdkljf;adjf',
#                 compilation_standard_error_output='amdsnf;s',
#                 valid=False,
#                 validity_check_standard_output='askdjf',
#                 validity_check_standard_error_output='ajdsnf',
#                 timed_out=False,
#                 buggy_implementations_exposed=[],
#             ),
#             StudentTestSuiteResult.new_test_evaluation_result_instance(
#                 'test_timeout.cpp',
#                 compilation_return_code=0,
#                 compilation_standard_output='asdkljf;adjf',
#                 compilation_standard_error_output='amdsnf;s',
#                 valid=False,
#                 validity_check_standard_output='askdjf',
#                 validity_check_standard_error_output='ajdsnf',
#                 timed_out=True,
#                 buggy_implementations_exposed=[],
#             )
#         ]


# class StudentTestSuiteResultTestCase(_SharedSetUp):
#     def test_valid_initialization_with_defaults(self):
#         result = StudentTestSuiteResult.objects.create(
#             test_suite=self.suite)

#         loaded = StudentTestSuiteResult.objects.get(pk=result.pk)
#         self.assertEqual(self.suite, loaded.test_suite)
#         self.assertIsNone(loaded.submission)
#         self.assertEqual(set(), loaded.buggy_implementations_exposed)
#         self.assertEqual([], loaded.detailed_results)

#     def test_valid_initialization_no_defaults(self):
#         exposed = set(['buggy1.cpp', 'buggy2.cpp'])
#         result = StudentTestSuiteResult.objects.create(
#             test_suite=self.suite,
#             submission=self.submission,
#             buggy_implementations_exposed=exposed,
#             detailed_results=self.detailed_suite_results
#         )

#         loaded = StudentTestSuiteResult.objects.get(pk=result.pk)
#         self.assertEqual(self.suite, loaded.test_suite)
#         self.assertEqual(self.submission, loaded.submission)
#         self.assertEqual(exposed, loaded.buggy_implementations_exposed)
#         self.assertListEqual(
#             self.detailed_suite_results, loaded.detailed_results)


# class StudentTestSuiteResultSerializerTestCase(_SharedSetUp):
#     def setUp(self):
#         super().setUp()

#         self.result = StudentTestSuiteResult.objects.create(
#             test_suite=self.suite,
#             submission=self.submission,
#             buggy_implementations_exposed=set(['buggy1.cpp', 'buggy2.cpp']),
#             detailed_results=self.detailed_suite_results
#         )

#         self.low_feedback_config = (
#             fbc.StudentTestSuiteFeedbackConfiguration())

#         self.medium_feedback_config = fbc.StudentTestSuiteFeedbackConfiguration(
#             compilation_feedback_level=(
#                 fbc.CompilationFeedbackLevel.success_or_failure_only),
#             student_test_validity_feedback_level=(
#                 fbc.StudentTestCaseValidityFeedbackLevel.show_valid_or_invalid),
#             buggy_implementations_exposed_feedback_level=(
#                 fbc.BuggyImplementationsExposedFeedbackLevel.list_implementations_exposed_overall),
#             points_feedback_level=fbc.PointsFeedbackLevel.show_total
#         )

#         self.full_feedback_config = fbc.StudentTestSuiteFeedbackConfiguration(
#             compilation_feedback_level=(
#                 fbc.CompilationFeedbackLevel.show_compiler_output),
#             student_test_validity_feedback_level=(
#                 fbc.StudentTestCaseValidityFeedbackLevel.show_validity_check_output),
#             buggy_implementations_exposed_feedback_level=(
#                 fbc.BuggyImplementationsExposedFeedbackLevel.list_implementations_exposed_per_test),
#             points_feedback_level=fbc.PointsFeedbackLevel.show_breakdown
#         )

#         self.low_feedback_result = {
#             'test_suite_name': self.suite.name,
#             'detailed_results': [
#                 {
#                     'student_test_case_name': res.student_test_case_name
#                 }
#                 for res in self.detailed_suite_results
#             ]
#         }

#         self.medium_feedback_result = {
#             'test_suite_name': self.suite.name,
#             'detailed_results': [
#                 {
#                     'student_test_case_name': res.student_test_case_name,
#                     'compilation_succeeded': res.compilation_return_code == 0,
#                     'valid': res.valid,
#                     'timed_out': res.timed_out
#                 }
#                 for res in self.detailed_suite_results
#             ],

#             'buggy_implementations_exposed': (
#                 self.suite.buggy_implementation_filenames),

#             'points_awarded': 4,
#             'points_possible': 4
#         }

#         self.full_feedback_result = {
#             'test_suite_name': self.suite.name,
#             'detailed_results': [
#                 {
#                     'student_test_case_name': res.student_test_case_name,
#                     'compilation_succeeded': res.compilation_return_code == 0,
#                     'compilation_standard_output': res.compilation_standard_output,
#                     'compilation_standard_error_output': res.compilation_standard_error_output,
#                     'valid': res.valid,
#                     'validity_check_standard_output': res.validity_check_standard_output,
#                     'validity_check_standard_error_output': res.validity_check_standard_error_output,
#                     'timed_out': res.timed_out,
#                     'buggy_implementations_exposed': res.buggy_implementations_exposed
#                 }
#                 for res in self.detailed_suite_results
#             ],

#             'buggy_implementations_exposed': (
#                 self.suite.buggy_implementation_filenames),

#             'points_awarded': 4,
#             'points_possible': 4
#         }

#     def test_to_json_low_feedback(self):
#         self.suite.feedback_configuration = self.low_feedback_config
#         self.suite.validate_and_save()

#         self.assertEqual(self.low_feedback_result, self.result.to_json())

#     def test_to_json_medium_feedback(self):
#         self.suite.feedback_configuration = self.medium_feedback_config
#         self.suite.validate_and_save()

#         self.assertEqual(self.medium_feedback_result, self.result.to_json())

#     def test_to_json_full_feedback(self):
#         feedback_config = self.full_feedback_config
#         self.suite.feedback_configuration = feedback_config
#         self.suite.validate_and_save()

#         self.assertEqual(self.full_feedback_result, self.result.to_json())

#     def test_to_json_with_submission_no_feedback_override(self):
#         self.suite.feedback_configuration = self.low_feedback_config
#         self.suite.validate_and_save()

#         self.assertEqual(self.low_feedback_result, self.result.to_json())

#     def test_to_json_with_manual_feedback_override(self):
#         self.suite.feedback_configuration = self.low_feedback_config

#         self.suite.validate_and_save()
#         self.submission.save()

#         self.assertEqual(
#             self.medium_feedback_result,
#             self.result.to_json(self.medium_feedback_config))

#     def test_to_json_with_post_deadline_override(self):
#         override = self.medium_feedback_config

#         self.suite.post_deadline_final_submission_feedback_configuration = (
#             override)
#         self.suite.validate_and_save()

#         self.assertEqual(self.medium_feedback_result, self.result.to_json())

#         extension = timezone.now() + datetime.timedelta(minutes=-1)

#         self.submission.submission_group.extended_due_date = extension
#         self.submission.save()

#         self.assertEqual(self.medium_feedback_result, self.result.to_json())

#     def test_serialize_results_with_post_deadline_override_but_user_has_extension(self):
#         override = self.medium_feedback_config

#         self.suite.post_deadline_final_submission_feedback_configuration = (
#             override)
#         self.suite.validate_and_save()

#         extension = timezone.now() + datetime.timedelta(minutes=1)

#         self.submission.submission_group.extended_due_date = extension
#         self.submission.save()

#         self.assertEqual(self.low_feedback_result, self.result.to_json())

#     def test_serialize_results_with_post_deadline_override_not_final_submission(self):
#         old_submission = Submission.objects.get(pk=self.submission.pk)
#         new_submission = self.submission
#         new_submission.pk = None
#         new_submission.save()

#         self.result.submission = old_submission
#         self.result.save()

#         self.assertNotEqual(old_submission, new_submission)
#         self.assertGreater(new_submission.pk, old_submission.pk)

#         override = self.medium_feedback_config

#         self.suite.post_deadline_final_submission_feedback_configuration = (
#             override)
#         self.suite.validate_and_save()

#         self.assertEqual(self.low_feedback_result, self.result.to_json())

#     def test_to_json_points_feedback_high_but_buggy_exposure_feedback_low(self):
#         for points_level in (fbc.PointsFeedbackLevel.show_total,
#                              fbc.PointsFeedbackLevel.show_breakdown):
#             self.low_feedback_config.points_feedback_level = points_level
#             self.suite.feedback_configuration = self.low_feedback_config
#             self.suite.validate_and_save()

#             self.assertEqual(self.low_feedback_result, self.result.to_json())
