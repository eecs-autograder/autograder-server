from django.core.files.uploadedfile import SimpleUploadedFile

from autograder.tests.temporary_filesystem_test_case import (
    TemporaryFilesystemTestCase)

import autograder.tests.dummy_object_utils as obj_ut

from autograder.models import (
    StudentTestSuiteFactory, SubmissionGroup, Submission, Project,
    StudentTestSuiteResult)

import autograder.models.feedback_configuration as fdbk_conf


class _SharedSetUp(TemporaryFilesystemTestCase):
    def setUp(self):
        super().setUp()

        self.maxDiff = None

        self.project = obj_ut.build_project({
            'expected_student_file_patterns': [
                Project.FilePatternTuple('test_*.cpp', 1, 3)
            ],
            'allow_submissions_from_non_enrolled_students': True
        })

        proj_files = [
            SimpleUploadedFile('correct.cpp', b'blah'),
            SimpleUploadedFile('buggy1.cpp', b'buuug'),
            SimpleUploadedFile('buggy2.cpp', b'buuug')
        ]
        for file_ in proj_files:
            self.project.add_project_file(file_)

        self.group = SubmissionGroup.objects.validate_and_create(
            members=['steve'], project=self.project)

        self.suite = StudentTestSuiteFactory.validate_and_create(
            'compiled_student_test_suite',
            name='suite',
            project=self.project,
            student_test_case_filename_pattern='test_*.cpp',
            correct_implementation_filename='correct.cpp',
            buggy_implementation_filenames=['buggy1.cpp', 'buggy2.cpp'],
            points_per_buggy_implementation_exposed=2
        )

        submitted_files = [
            SimpleUploadedFile('test_1.cpp', b'asdf'),
            SimpleUploadedFile('test_2.cpp', b'asdf'),
            SimpleUploadedFile('test_expose_none.cpp', b'asdf'),
            SimpleUploadedFile('test_no_compile.cpp', b'asdf'),
            SimpleUploadedFile('test_invalid.cpp', b'asdf'),
            SimpleUploadedFile('test_timeout.cpp', b'asdf')
        ]
        self.submission = Submission.objects.validate_and_create(
            submission_group=self.group,
            submitted_files=submitted_files)

        self.detailed_suite_results = [
            StudentTestSuiteResult.new_test_evaluation_result_instance(
                'test_1.cpp',
                compilation_return_code=0,
                compilation_standard_output='asdkljf;adjf',
                compilation_standard_error_output='amdsnf;s',
                valid=True,
                validity_check_standard_output='askdjf',
                validity_check_standard_error_output='ajdsnf',
                timed_out=False,
                buggy_implementations_exposed=['buggy1.cpp']
            ),
            StudentTestSuiteResult.new_test_evaluation_result_instance(
                'test_2.cpp',
                compilation_return_code=0,
                compilation_standard_output='asdkljf;adjf',
                compilation_standard_error_output='amdsnf;s',
                valid=True,
                validity_check_standard_output='askdjf',
                validity_check_standard_error_output='ajdsnf',
                timed_out=False,
                buggy_implementations_exposed=['buggy2.cpp']
            ),
            StudentTestSuiteResult.new_test_evaluation_result_instance(
                'test_expose_none.cpp',
                compilation_return_code=0,
                compilation_standard_output='asdkljf;adjf',
                compilation_standard_error_output='amdsnf;s',
                valid=True,
                validity_check_standard_output='askdjf',
                validity_check_standard_error_output='ajdsnf',
                timed_out=False,
                buggy_implementations_exposed=[]
            ),
            StudentTestSuiteResult.new_test_evaluation_result_instance(
                'test_no_compile.cpp',
                compilation_return_code=42,
                compilation_standard_output='asdkljf;adjf',
                compilation_standard_error_output='amdsnf;s',
                valid=None,
                validity_check_standard_output=None,
                validity_check_standard_error_output=None,
                timed_out=None,
                buggy_implementations_exposed=[]
            ),
            StudentTestSuiteResult.new_test_evaluation_result_instance(
                'test_invalid.cpp',
                compilation_return_code=0,
                compilation_standard_output='asdkljf;adjf',
                compilation_standard_error_output='amdsnf;s',
                valid=False,
                validity_check_standard_output='askdjf',
                validity_check_standard_error_output='ajdsnf',
                timed_out=False,
                buggy_implementations_exposed=[]
            ),
            StudentTestSuiteResult.new_test_evaluation_result_instance(
                'test_timeout.cpp',
                compilation_return_code=0,
                compilation_standard_output='asdkljf;adjf',
                compilation_standard_error_output='amdsnf;s',
                valid=False,
                validity_check_standard_output='askdjf',
                validity_check_standard_error_output='ajdsnf',
                timed_out=True,
                buggy_implementations_exposed=[]
            )
        ]


class StudentTestSuiteResultTestCase(_SharedSetUp):
    def test_valid_initialization_with_defaults(self):
        result = StudentTestSuiteResult.objects.create(
            test_suite=self.suite)

        loaded = StudentTestSuiteResult.objects.get(pk=result.pk)
        self.assertEqual(self.suite, loaded.test_suite)
        self.assertIsNone(loaded.submission)
        self.assertEqual(set(), loaded.buggy_implementations_exposed)
        self.assertEqual([], loaded.detailed_results)

    def test_valid_initialization_no_defaults(self):
        exposed = set(['buggy1.cpp', 'buggy2.cpp'])
        result = StudentTestSuiteResult.objects.create(
            test_suite=self.suite,
            submission=self.submission,
            buggy_implementations_exposed=exposed,
            detailed_results=self.detailed_suite_results
        )

        loaded = StudentTestSuiteResult.objects.get(pk=result.pk)
        self.assertEqual(self.suite, loaded.test_suite)
        self.assertEqual(self.submission, loaded.submission)
        self.assertEqual(exposed, loaded.buggy_implementations_exposed)
        self.assertListEqual(
            self.detailed_suite_results, loaded.detailed_results)


class StudentTestSuiteResultSerializerTestCase(_SharedSetUp):
    def setUp(self):
        super().setUp()
        self.result = StudentTestSuiteResult.objects.create(
            test_suite=self.suite,
            submission=self.submission,
            buggy_implementations_exposed=set(['buggy1.cpp', 'buggy2.cpp']),
            detailed_results=self.detailed_suite_results
        )

        self.low_feedback_config = (
            fdbk_conf.StudentTestSuiteFeedbackConfiguration())

        self.medium_feedback_config = fdbk_conf.StudentTestSuiteFeedbackConfiguration(
            compilation_feedback_level=(
                fdbk_conf.CompilationFeedbackLevel.success_or_failure_only),
            student_test_validity_feedback_level=(
                fdbk_conf.StudentTestCaseValidityFeedbackLevel.show_valid_or_invalid),
            buggy_implementations_exposed_feedback_level=(
                fdbk_conf.BuggyImplementationsExposedFeedbackLevel.list_implementations_exposed_overall),
            points_feedback_level=fdbk_conf.PointsFeedbackLevel.show_total
        )

        self.full_feedback_config = fdbk_conf.StudentTestSuiteFeedbackConfiguration(
            compilation_feedback_level=(
                fdbk_conf.CompilationFeedbackLevel.show_compiler_output),
            student_test_validity_feedback_level=(
                fdbk_conf.StudentTestCaseValidityFeedbackLevel.show_validity_check_output),
            buggy_implementations_exposed_feedback_level=(
                fdbk_conf.BuggyImplementationsExposedFeedbackLevel.list_implementations_exposed_per_test),
            points_feedback_level=fdbk_conf.PointsFeedbackLevel.show_breakdown
        )

        self.low_feedback_result = {
            'test_suite_name': self.suite.name,
            'detailed_results': [
                {
                    'student_test_case_name': res.student_test_case_name
                }
                for res in self.detailed_suite_results
            ]
        }

        self.medium_feedback_result = {
            'test_suite_name': self.suite.name,
            'detailed_results': [
                {
                    'student_test_case_name': res.student_test_case_name,
                    'compilation_succeeded': res.compilation_return_code == 0,
                    'valid': res.valid,
                    'timed_out': res.timed_out
                }
                for res in self.detailed_suite_results
            ],

            'buggy_implementations_exposed': (
                self.suite.buggy_implementation_filenames),

            'points_awarded': 4,
            'points_possible': 4
        }

        self.full_feedback_result = {
            'test_suite_name': self.suite.name,
            'detailed_results': [
                {
                    'student_test_case_name': res.student_test_case_name,
                    'compilation_succeeded': res.compilation_return_code == 0,
                    'compilation_standard_output': res.compilation_standard_output,
                    'compilation_standard_error_output': res.compilation_standard_error_output,
                    'valid': res.valid,
                    'validity_check_standard_output': res.validity_check_standard_output,
                    'validity_check_standard_error_output': res.validity_check_standard_error_output,
                    'timed_out': res.timed_out,
                    'buggy_implementations_exposed': res.buggy_implementations_exposed
                }
                for res in self.detailed_suite_results
            ],

            'buggy_implementations_exposed': (
                self.suite.buggy_implementation_filenames),

            'points_awarded': 4,
            'points_possible': 4
        }

    def test_to_json_low_feedback(self):
        self.project.student_test_suite_feedback_configuration = (
            self.low_feedback_config)
        self.project.validate_and_save()

        self.assertEqual(self.low_feedback_result, self.result.to_json())

    def test_to_json_medium_feedback(self):
        self.project.student_test_suite_feedback_configuration = (
            self.medium_feedback_config)
        self.project.validate_and_save()

        self.assertEqual(self.medium_feedback_result, self.result.to_json())

    def test_to_json_full_feedback(self):
        feedback_config = self.full_feedback_config
        self.project.student_test_suite_feedback_configuration = (
            feedback_config)
        self.project.validate_and_save()

        self.assertEqual(self.full_feedback_result, self.result.to_json())

    def test_to_json_with_submission_no_feedback_override(self):
        self.project.student_test_suite_feedback_configuration = (
            self.low_feedback_config)
        self.project.validate_and_save()

        self.assertEqual(self.low_feedback_result, self.result.to_json())

    def test_to_json_with_submission_feedback_override(self):
        self.project.student_test_suite_feedback_configuration = (
            self.low_feedback_config)
        self.submission.student_test_suite_feedback_config_override = (
            self.medium_feedback_config)

        self.project.validate_and_save()
        self.submission.save()

        self.assertEqual(self.medium_feedback_result, self.result.to_json())

    def test_to_json_with_manual_feedback_override(self):
        self.project.student_test_suite_feedback_configuration = (
            self.low_feedback_config)

        self.project.validate_and_save()
        self.submission.save()

        self.assertEqual(
            self.medium_feedback_result,
            self.result.to_json(self.medium_feedback_config))

    def test_to_json_with_submission_and_manual_feedback_override(self):
        self.project.student_test_suite_feedback_configuration = (
            self.low_feedback_config)
        self.submission.student_test_suite_feedback_config_override = (
            self.medium_feedback_result)

        self.project.validate_and_save()
        self.submission.save()

        self.assertEqual(
            self.full_feedback_result,
            self.result.to_json(self.full_feedback_config))

    def test_to_json_points_feedback_high_but_buggy_exposure_feedback_low(self):
        for points_level in (fdbk_conf.PointsFeedbackLevel.show_total,
                             fdbk_conf.PointsFeedbackLevel.show_breakdown):
            self.low_feedback_config.points_feedback_level = points_level
            self.project.student_test_suite_feedback_configuration = (
                self.low_feedback_config)
            self.project.validate_and_save()

            self.assertEqual(self.low_feedback_result, self.result.to_json())
