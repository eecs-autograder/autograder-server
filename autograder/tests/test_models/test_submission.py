from django.contrib.auth.models import User

from autograder.tests.temporary_filesystem_test_case import (
    TemporaryFilesystemTestCase)

from autograder.models import (
    Course, Semester, Project, Submission, SubmissionGroup)


def _make_dummy_user(username, password):
    user = User.objects.create(username=username)
    user.set_password(password)
    return user


class SubmissionTestCase(TemporaryFilesystemTestCase):
    def setUp(self):
        super().setUp()

        self.course = Course.objects.create(name='eecs280')
        self.semester = Semester.objects.create(name='f15', course=self.course)

        self.project = Project.objects.create(
            name='my_project', semester=self.semester, max_group_size=2)

        self.group_members = [
            _make_dummy_user('steve', 'spam'),
            _make_dummy_user('joe', 'eggs')
        ]

        self.submission_group = SubmissionGroup.objects.create_group(
            self.group_members, self.project)

    def test_valid_init(self):
        submission = Submission.objects.create(
            submission_group=self.submission_group)

        loaded_submission = Submission.objects.get(
            submission_group=self.submission_group)

        self.assertEqual(loaded_submission, submission)
        self.assertEqual(
            loaded_submission.submission_group, self.submission_group)
        self.assertEqual(loaded_submission.timestamp, submission.timestamp)
