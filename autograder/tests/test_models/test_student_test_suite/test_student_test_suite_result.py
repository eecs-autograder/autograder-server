from django.core.files.uploadedfile import SimpleUploadedFile

from autograder.tests.temporary_filesystem_test_case import (
    TemporaryFilesystemTestCase)

import autograder.tests.dummy_object_utils as obj_ut

from autograder.models import (
    StudentTestSuiteFactory, SubmissionGroup, Submission, Project,
    StudentTestSuiteResult)


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
            buggy_implementation_filenames=['buggy1.cpp', 'buggy2.cpp']
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
        self.assertListEqual(self.detailed_suite_results, loaded.detailed_results)


class StudentTestSuiteResultSerializerTestCase(_SharedSetUp):
    def test_to_json_low_feedback(self):
        self.fail()

    def test_to_json_medium_feedback(self):
        self.fail()

    def test_to_json_full_feedback(self):
        self.fail()

    def test_to_json_with_submission_no_feedback_override(self):
        self.fail()

    def test_to_json_with_submission_feedback_override(self):
        self.fail()

    def test_to_json_with_manual_feedback_override(self):
        self.fail()

    def test_to_json_with_submission_and_manual_feedback_override(self):
        self.fail()
