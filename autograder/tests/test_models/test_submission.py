# from django.contrib.auth.models import User
# from django.core.exceptions import ValidationError
# from django.core.files.uploadedfile import SimpleUploadedFile

# from autograder.tests.temporary_filesystem_test_case import (
#     TemporaryFilesystemTestCase)

# from autograder.models import (
#     Course, Semester, Project, Submission, SubmissionGroup)


# def _make_dummy_user(username, password):
#     user = User.objects.create(username=username)
#     user.set_password(password)
#     return user


# class SubmissionTestCase(TemporaryFilesystemTestCase):
#     def setUp(self):
#         super().setUp()

#         self.course = Course.objects.create(name='eecs280')
#         self.semester = Semester.objects.create(name='f15', course=self.course)

#         self.project = Project.objects.create(
#             name='my_project', semester=self.semester, max_group_size=2)
#         self.project.add_required_student_files('spam.cpp', 'eggs.cpp')
#         self.project.add_expected_student_file_pattern('test_*.cpp', 1, 2)

#         self.group_members = [
#             _make_dummy_user('steve', 'spam'),
#             _make_dummy_user('joe', 'eggs')
#         ]

#         self.submission_group = SubmissionGroup.objects.create_group(
#             self.group_members, self.project)

#     def test_valid_init(self):
#         submitted_files = [
#             SimpleUploadedFile('spam.cpp', b'blah'),
#             SimpleUploadedFile('eggs.cpp', b'merp'),
#             SimpleUploadedFile('test_spam.cpp', b'cheeese')
#         ]
#         submission = Submission.objects.validate_and_create(
#             submission_group=self.submission_group,
#             submitted_files=submitted_files)

#         loaded_submission = Submission.objects.get(
#             submission_group=self.submission_group)

#         self.assertEqual(loaded_submission, submission)
#         self.assertEqual(
#             loaded_submission.submission_group, self.submission_group)
#         self.assertEqual(loaded_submission.timestamp, submission.timestamp)

#         for index, value in enumerate(sorted(loaded_submission.submitted_files)):
#             self.assertEqual(submitted_files[index], value)

#     def test_exception_on_submission_missing_files(self):
#         with self.assertRaises(ValidationError):
#             Submission.objects.validate_and_create(
#                 submission_group=self.submission_group,
#                 submitted_files=[
#                     SimpleUploadedFile('eggs.cpp', b'merp'),
#                     SimpleUploadedFile('test_spam.cpp', b'cheeese')])

#         with self.assertRaises(ValidationError):
#             Submission.objects.validate_and_create(
#                 submission_group=self.submission_group,
#                 submitted_files=[
#                     SimpleUploadedFile('spam.cpp', b'blah'),
#                     SimpleUploadedFile('eggs.cpp', b'merp')])

#     def test_exception_on_extra_file_no_ignore(self):
#         with self.assertRaises(ValidationError):
#             Submission.objects.validate_and_create(
#                 submission_group=self.submission_group,
#                 ignore_extra_files=False,
#                 submitted_files=[
#                     SimpleUploadedFile('spam.cpp', b'blah'),
#                     SimpleUploadedFile('eggs.cpp', b'merp'),
#                     SimpleUploadedFile('test_spam.cpp', b'cheeese'),
#                     SimpleUploadedFile('extra.cpp', b'toomuch')])

#     def test_no_exception_on_extra_file_with_ignore(self):
#         with self.assertRaises(ValidationError):
#             Submission.objects.validate_and_create(
#                 submission_group=self.submission_group,
#                 submitted_files=[
#                     SimpleUploadedFile('spam.cpp', b'blah'),
#                     SimpleUploadedFile('eggs.cpp', b'merp'),
#                     SimpleUploadedFile('test_spam.cpp', b'cheeese'),
#                     SimpleUploadedFile('extra.cpp', b'toomuch')])
