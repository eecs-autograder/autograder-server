# import unittest

# from django.core.files.uploadedfile import SimpleUploadedFile
# from django.core.exceptions import ValidationError
# from django.contrib.auth.models import User

# from autograder.models import (
#     Course, Semester, Project, AutograderTestCaseFactory,
#     SubmissionGroup, Submission)

# from autograder.models.fields import FeedbackConfiguration

# from autograder.tasks import grade_submission

# from autograder.tests.temporary_filesystem_test_case import (
#     TemporaryFilesystemTestCase)


# class GradeSubmissionTestCase(TemporaryFilesystemTestCase):
#     def setUp(self):
#         super().setUp()

#         self.user = User.objects.create(username='steve')
#         self.course = Course.objects.validate_and_create(name='coursey')
#         self.semester = Semester.objects.validate_and_create(
#             name='a semester', course=self.course)
#         self.project = Project.objects.validate_and_create(
#             name='projy', semester=self.semester,
#             allow_submissions_from_non_enrolled_students=True,
#             required_student_files=['hello.cpp', 'spam.cpp'],
#             test_case_feedback_configuration=FeedbackConfiguration.get_max_feedback())
#         self.project.add_project_file(SimpleUploadedFile('hello.h', HELLO_H))
#         self.project.add_project_file(SimpleUploadedFile('spam.h', SPAM_H))
#         self.project.add_project_file(
#             SimpleUploadedFile('test_hello.cpp', TEST_HELLO_CPP))
#         self.project.add_project_file(
#             SimpleUploadedFile('test_spam.cpp', TEST_SPAM_CPP))

#         AutograderTestCaseFactory.validate_and_create(
#             'compiled_test_case', name='test_hello',
#             project=self.project,
#             hide_from_students=False,
#             test_resource_files=['test_hello.cpp', 'hello.h'],
#             student_resource_files=['hello.cpp'],
#             expected_return_code=0,
#             expected_standard_output='hello\n',
#             use_valgrind=True,
#             points_for_correct_return_code=1,
#             points_for_correct_output=2,
#             points_for_compilation_success=1,
#             points_for_no_valgrind_errors=1,
#             compiler='g++',
#             compiler_flags=['-Wall', '-pedantic'],
#             files_to_compile_together=['test_hello.cpp', 'hello.cpp'],
#             executable_name='hello_prog')

#         AutograderTestCaseFactory.validate_and_create(
#             'compiled_test_case', name='test_spam',
#             project=self.project,
#             hide_from_students=False,
#             test_resource_files=['test_spam.cpp', 'spam.h'],
#             student_resource_files=['spam.cpp'],
#             expected_return_code=0,
#             use_valgrind=True,
#             points_for_correct_return_code=2,
#             points_for_compilation_success=1,
#             points_for_no_valgrind_errors=1,
#             compiler='g++',
#             compiler_flags=['-Wall', '-pedantic'],
#             files_to_compile_together=['test_spam.cpp', 'spam.cpp'],
#             executable_name='spam_prog')

#         AutograderTestCaseFactory.validate_and_create(
#             'compilation_only_test_case', name='test_hello_compilation',
#             project=self.project,
#             hide_from_students=False,
#             test_resource_files=['test_hello.cpp', 'hello.h'],
#             student_resource_files=['hello.cpp'],
#             points_for_compilation_success=1,
#             compiler='g++',
#             compiler_flags=['-Wall', '-pedantic'],
#             files_to_compile_together=['test_hello.cpp', 'hello.cpp'])

#         self.group = SubmissionGroup.objects.validate_and_create(
#             members=['steve'], project=self.project)

#         self.submission = Submission.objects.validate_and_create(
#             submission_group=self.group,
#             submitted_files=[SimpleUploadedFile('spam.cpp', SPAM_CPP),
#                              SimpleUploadedFile('hello.cpp', HELLO_CPP)])

#     def test_grade_submission(self):
#         grade_submission(self.submission.pk)
#         loaded = Submission.objects.get(pk=self.submission.pk)
#         results = loaded.results.all()

#         total_points = sum(
#             result.to_json()['total_points_awarded'] for result in results)

#         self.assertEqual('finished_grading', loaded.status)
#         self.assertEqual(10, total_points)


# HELLO_H = b"""#ifndef HELLO_H
# #define HELLO_H

# void hello();

# #endif
# """

# SPAM_H = b"""#ifndef SPAM_H
# #define SPAM_H

# int spam();

# #endif
# """

# TEST_HELLO_CPP = b"""#include "hello.h"

# int main()
# {
#     hello();
#     return 0;
# }
# """

# TEST_SPAM_CPP = b"""#include "spam.h"
# #include <cassert>

# int main()
# {
#     assert(spam() == 42);
# }
# """

# HELLO_CPP = b"""#include "hello.h"
# #include <iostream>

# using namespace std;

# void hello()
# {
#     cout << "hello" << endl;
# }
# """

# SPAM_CPP = b"""#include "spam.h"

# int spam()
# {
#     return 42;
# }
# """
