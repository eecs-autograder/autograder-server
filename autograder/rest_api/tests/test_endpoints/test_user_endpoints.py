import itertools

from django.core.urlresolvers import reverse
from django.utils import dateparse

from autograder.core.models import SubmissionGroupInvitation, Notification
from autograder.core.tests.temporary_filesystem_test_case import (
    TemporaryFilesystemTestCase)
import autograder.core.tests.dummy_object_utils as obj_ut
from .utilities import MockClient, json_load_bytes


class GetUserEndpointTestCase(TemporaryFilesystemTestCase):
    def setUp(self):
        super().setUp()

    def test_user_get_self(self):
        user = obj_ut.create_dummy_user()
        client = MockClient(user)

        expected_content = {
            "type": "user",
            "id": user.pk,
            "username": user.username,

            "urls": {
                "self": reverse('user:get', kwargs={'pk': user.pk}),

                "courses_is_admin_for": reverse(
                    'user:admin-courses', kwargs={'pk': user.pk}),
                "semesters_is_staff_for": reverse(
                    'user:staff-semesters', kwargs={'pk': user.pk}),
                "semesters_is_enrolled_in": reverse(
                    'user:enrolled-semesters', kwargs={'pk': user.pk}),
                "groups_is_member_of": reverse(
                    'user:submission-groups', kwargs={'pk': user.pk}),

                "group_invitations_sent": reverse(
                    'user:invitations-sent', kwargs={'pk': user.pk}),

                "group_invitations_received": reverse(
                    'user:invitations-received', kwargs={'pk': user.pk}),

                "notifications": reverse(
                    'user:notifications', kwargs={'pk': user.pk})
            }
        }
        response = client.get(reverse('user:get', kwargs={'pk': user.pk}))

        self.assertEqual(200, response.status_code)
        self.assertEqual(expected_content, json_load_bytes(response.content))

    def test_other_get_user_permission_denied(self):
        requester = obj_ut.create_dummy_user()
        requested = obj_ut.create_dummy_user()

        client = MockClient(requester)

        response = client.get(
            reverse('user:get', kwargs={'pk': requested.pk}))

        self.assertEqual(403, response.status_code)

    # def test_user_not_found(self):
    #     client = MockClient(obj_ut.create_dummy_user())

    #     response = client.get(
    #         reverse('user:get', kwargs={'pk': 750}))

    #     self.assertEqual(404, response.status_code)

# -----------------------------------------------------------------------------
# -----------------------------------------------------------------------------


class GetCoursesIsAdminForTestCase(TemporaryFilesystemTestCase):
    def setUp(self):
        super().setUp()

        self.admin = obj_ut.create_dummy_user()
        self.other = obj_ut.create_dummy_user()

        self.courses = [
            obj_ut.build_course(
                course_kwargs={'administrators': [self.admin]})
            for i in range(2)
        ]

        self.assertEqual(2, self.admin.courses_is_admin_for.count())

    def test_user_get_self_courses_is_admin_for(self):
        for user in self.admin, self.other:
            client = MockClient(user)

            expected_content = {
                "courses": [
                    {
                        'name': course.name,
                        'url': reverse('course:get', kwargs={'pk': course.pk})
                    }
                    for course in sorted(
                        user.courses_is_admin_for.all(),
                        key=lambda obj: obj.name)
                ]
            }

            response = client.get(
                reverse('user:admin-courses', kwargs={'pk': user.pk}))

            self.assertEqual(200, response.status_code)

            actual_content = json_load_bytes(response.content)
            actual_content['courses'] = sorted(
                actual_content['courses'], key=lambda obj: obj['name'])

            self.assertEqual(expected_content, actual_content)

    def test_permission_denied_other_user_get_courses_is_admin_for(self):
        pairs = (
            (self.admin, self.other), (self.other, self.admin))
        for requester, requested in pairs:
            client = MockClient(requester)
            response = client.get(
                reverse('user:admin-courses', kwargs={'pk': requested.pk}))
            self.assertEqual(403, response.status_code)

# -----------------------------------------------------------------------------
# -----------------------------------------------------------------------------


class GetSemestersIsStaffForTestCase(TemporaryFilesystemTestCase):
    def setUp(self):
        super().setUp()

        self.staff = obj_ut.create_dummy_user()
        self.other = obj_ut.create_dummy_user()

        self.courses = [
            obj_ut.build_semester(
                semester_kwargs={'staff': [self.staff]})
            for i in range(2)
        ]

        self.assertEqual(2, self.staff.semesters_is_staff_for.count())

    def test_user_get_self_semesters_is_staff_for(self):
        for user in self.staff, self.other:
            client = MockClient(user)

            expected_content = {
                'semesters': [
                    {
                        'name': semester.name,
                        'url': reverse(
                            'semester:get', kwargs={'pk': semester.pk})
                    }
                    for semester in sorted(
                        user.semesters_is_staff_for.all(),
                        key=lambda obj: obj.name)
                ]
            }

            response = client.get(
                reverse('user:staff-semesters', kwargs={'pk': user.pk}))

            self.assertEqual(200, response.status_code)
            actual_content = json_load_bytes(response.content)

            actual_content['semesters'] = sorted(
                actual_content['semesters'], key=lambda obj: obj['name'])

            self.assertEqual(expected_content, actual_content)

    def test_permission_denied_get_other_semesters_is_staff_for(self):
        pairs = (
            (self.staff, self.other), (self.other, self.staff))
        for requester, requested in pairs:
            client = MockClient(requester)
            response = client.get(
                reverse('user:staff-semesters', kwargs={'pk': requested.pk}))
            self.assertEqual(403, response.status_code)

# -----------------------------------------------------------------------------
# -----------------------------------------------------------------------------


class GetSemestersIsEnrolledInTestCase(TemporaryFilesystemTestCase):
    def setUp(self):
        super().setUp()

        self.enrolled = obj_ut.create_dummy_user()
        self.other = obj_ut.create_dummy_user()

        self.courses = [
            obj_ut.build_semester(
                semester_kwargs={'enrolled_students': [self.enrolled]})
            for i in range(2)
        ]

        self.assertEqual(2, self.enrolled.semesters_is_enrolled_in.count())

    def test_user_get_self_semesters_is_enrolled_in(self):
        for user in self.enrolled, self.other:
            client = MockClient(user)

            expected_content = {
                'semesters': [
                    {
                        'name': semester.name,
                        'url': reverse(
                            'semester:get', kwargs={'pk': semester.pk})
                    }
                    for semester in sorted(
                        user.semesters_is_enrolled_in.all(),
                        key=lambda obj: obj.name)
                ]
            }

            response = client.get(
                reverse('user:enrolled-semesters', kwargs={'pk': user.pk}))

            self.assertEqual(200, response.status_code)
            actual_content = json_load_bytes(response.content)

            actual_content['semesters'] = sorted(
                actual_content['semesters'], key=lambda obj: obj['name'])

            self.assertEqual(expected_content, actual_content)

    def test_permission_denied_get_other_semesters_is_enrolled_in(self):
        pairs = (
            (self.enrolled, self.other), (self.other, self.enrolled))
        for requester, requested in pairs:
            client = MockClient(requester)
            response = client.get(
                reverse('user:enrolled-semesters',
                        kwargs={'pk': requested.pk}))
            self.assertEqual(403, response.status_code)

# -----------------------------------------------------------------------------
# -----------------------------------------------------------------------------


class GetGroupsIsMemberOfTestCase(TemporaryFilesystemTestCase):
    def setUp(self):
        super().setUp()

        self.member = obj_ut.create_dummy_user()
        self.other = obj_ut.create_dummy_user()

        self.groups = [
            obj_ut.build_submission_group(
                group_kwargs={'members': [self.member]},
                project_kwargs={
                    'allow_submissions_from_non_enrolled_students': True})
            for i in range(2)
        ]

        self.assertEqual(2, self.member.groups_is_member_of.count())

    def test_user_get_self_groups_is_member_of(self):
        for user in self.member, self.other:
            client = MockClient(user)

            expected_content = {
                'groups': [
                    {
                        'project_name': group.project.name,
                        'url': reverse(
                            'group:get', kwargs={'pk': group.pk})
                    }
                    for group in sorted(
                        user.groups_is_member_of.all(),
                        key=lambda obj: obj.project.name)
                ]
            }

            response = client.get(
                reverse('user:submission-groups', kwargs={'pk': user.pk}))

            self.assertEqual(200, response.status_code)
            actual_content = json_load_bytes(response.content)

            actual_content['groups'] = sorted(
                actual_content['groups'], key=lambda obj: obj['project_name'])

            self.assertEqual(expected_content, actual_content)

    def test_permission_denied_get_other_groups_is_member_of(self):
        pairs = (
            (self.member, self.other), (self.other, self.member))
        for requester, requested in pairs:
            client = MockClient(requester)
            response = client.get(
                reverse('user:submission-groups',
                        kwargs={'pk': requested.pk}))
            self.assertEqual(403, response.status_code)

# -----------------------------------------------------------------------------
# -----------------------------------------------------------------------------


class GetGroupInvitationsSentOrReceivedTestCase(TemporaryFilesystemTestCase):
    def setUp(self):
        super().setUp()

        self.project = obj_ut.build_project(
            project_kwargs={
                'allow_submissions_from_non_enrolled_students': True,
                'max_group_size': 4})

        self.invitor = obj_ut.create_dummy_user()
        self.invitees = obj_ut.create_dummy_users(2)

        self.invitations = [
            SubmissionGroupInvitation.objects.validate_and_create(
                invitation_creator=self.invitor.username,
                invited_users=[user.username for user in self.invitees],
                project=self.project)
            for i in range(2)
        ]

        self.assertEqual(2, self.invitor.group_invitations_sent.count())
        self.assertEqual(
            2, self.invitees[0].group_invitations_received.count())

        self.assertEqual(0, self.invitees[0].group_invitations_sent.count())
        self.assertEqual(
            0, self.invitor.group_invitations_received.count())

        self.other = obj_ut.create_dummy_user()

    def test_user_get_own_sent_invitations(self):
        for user in self.invitor, self.invitees[0]:
            client = MockClient(user)
            expected_content = {
                "group_requests": [
                    {
                        "project_name": invitation.project.name,
                        "request_sender": (
                            invitation.invitation_creator.username),
                        "url": reverse(
                            'invitation:get', kwargs={'pk': invitation.pk})
                    }
                    for invitation in sorted(
                        user.group_invitations_sent.all(),
                        key=lambda obj: obj.project.name)
                ]
            }

            response = client.get(
                reverse('user:invitations-sent', kwargs={'pk': user.pk}))

            self.assertEqual(200, response.status_code)

            actual_content = json_load_bytes(response.content)
            actual_content['group_requests'] = sorted(
                actual_content['group_requests'],
                key=lambda obj: obj['project_name'])
            self.assertEqual(expected_content, actual_content)

    def test_user_get_other_sent_invitations_permission_denied(self):
        pairs = (
            (self.invitor, self.invitees[0]), (self.invitees[0], self.invitor))
        for requester, requested in pairs:
            client = MockClient(requester)
            response = client.get(
                reverse('user:invitations-sent',
                        kwargs={'pk': requested.pk}))
            self.assertEqual(403, response.status_code)

    def test_user_get_own_recieved_invitations(self):
        for user in self.invitor, self.invitees[0]:
            client = MockClient(user)
            expected_content = {
                "group_requests": [
                    {
                        "project_name": invitation.project.name,
                        "request_sender": (
                            invitation.invitation_creator.username),
                        "url": reverse(
                            'invitation:get', kwargs={'pk': invitation.pk})
                    }
                    for invitation in sorted(
                        user.group_invitations_received.all(),
                        key=lambda obj: obj.project.name)
                ]
            }

            response = client.get(
                reverse('user:invitations-received', kwargs={'pk': user.pk}))

            self.assertEqual(200, response.status_code)

            actual_content = json_load_bytes(response.content)
            actual_content['group_requests'] = sorted(
                actual_content['group_requests'],
                key=lambda obj: obj['project_name'])
            self.assertEqual(expected_content, actual_content)

    def test_user_get_other_recieved_invitations_permission_denied(self):
        pairs = (
            (self.invitor, self.invitees[0]), (self.invitees[0], self.invitor))
        for requester, requested in pairs:
            client = MockClient(requester)
            response = client.get(
                reverse('user:invitations-received',
                        kwargs={'pk': requested.pk}))
            self.assertEqual(403, response.status_code)

# -----------------------------------------------------------------------------
# -----------------------------------------------------------------------------


class GetNotificationsTestCase(TemporaryFilesystemTestCase):
    def setUp(self):
        super().setUp()

        self.user = obj_ut.create_dummy_user()
        self.other = obj_ut.create_dummy_user()

        self.notifications = [
            Notification.objects.create(
                message='helloooo', recipient=self.user)
            for i in range(2)
        ]

        self.assertEqual(2, self.user.notifications.count())
        self.assertEqual(0, self.other.notifications.count())

    def test_user_get_self_notifications(self):
        for user in self.user, self.other:
            client = MockClient(user)
            expected_content = {
                "notifications": [
                    {
                        "timestamp": notification.timestamp.replace(
                            microsecond=0),
                        "url": reverse('notification:get',
                                       kwargs={'pk': notification.pk})
                    }
                    for notification in sorted(
                        user.notifications.all(), key=lambda obj: obj.pk)
                ]
            }

            response = client.get(
                reverse('user:notifications', kwargs={'pk': user.pk}))

            self.assertEqual(200, response.status_code)

            actual_content = json_load_bytes(response.content)
            actual_content['notifications'] = sorted(
                actual_content['notifications'], key=lambda obj: obj['url'])
            for obj in actual_content['notifications']:
                obj['timestamp'] = dateparse.parse_datetime(
                    obj['timestamp']).replace(microsecond=0)
            self.assertEqual(expected_content, actual_content)

    def test_permission_denied_get_other_notifications(self):
        pairs = (
            (self.user, self.other), (self.other, self.user))
        for requester, requested in pairs:
            client = MockClient(requester)
            response = client.get(
                reverse('user:notifications',
                        kwargs={'pk': requested.pk}))
            self.assertEqual(403, response.status_code)

# -----------------------------------------------------------------------------
# -----------------------------------------------------------------------------


class GetNotificationEndpointTestCase(TemporaryFilesystemTestCase):
    def setUp(self):
        super().setUp()

        self.user = obj_ut.create_dummy_user()
        self.other = obj_ut.create_dummy_user()

        self.notification = Notification.objects.create(
            message='helloooo', recipient=self.user)

        self.notification_url = reverse(
            'notification:get', kwargs={'pk': self.notification.pk})

    def test_user_get_own_notification(self):
        client = MockClient(self.user)

        expected_content = {
            "type": "notification",
            "id": self.notification.pk,
            "timestamp": self.notification.timestamp.replace(microsecond=0),
            "message": self.notification.message,

            "urls": {
                "self": self.notification_url,
                "user": reverse('user:get', kwargs={'pk': self.user.pk})
            }
        }

        response = client.get(self.notification_url)
        self.assertEqual(200, response.status_code)
        actual_content = json_load_bytes(response.content)
        actual_content['timestamp'] = dateparse.parse_datetime(
            actual_content['timestamp']).replace(microsecond=0)
        self.assertEqual(expected_content, actual_content)

    def test_user_get_other_user_notification_permission_denied(self):
        client = MockClient(self.other)
        response = client.get(self.notification_url)
        self.assertEqual(403, response.status_code)
