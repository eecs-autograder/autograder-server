import datetime

from django.core.urlresolvers import reverse
from django.utils import timezone
from django.core.files.uploadedfile import SimpleUploadedFile
from django.core.exceptions import ObjectDoesNotExist
from django.contrib.auth.models import User

from autograder.core.models import (
    Project, AutograderTestCaseFactory, AutograderTestCaseBase,
    StudentTestSuiteFactory, StudentTestSuiteBase, SubmissionGroup,
    SubmissionGroupInvitation)

from autograder.core.tests.temporary_filesystem_test_case import (
    TemporaryFilesystemTestCase)
import autograder.core.tests.dummy_object_utils as obj_ut
from .utilities import MockClient, json_load_bytes, sorted_by_pk

from autograder.rest_api.endpoints.project_endpoints import (
    DEFAULT_SUBMISSION_GROUP_PAGE_SIZE
)


def _common_setup(fixture):
    fixture.admin = obj_ut.create_dummy_user()
    fixture.staff = obj_ut.create_dummy_user()
    fixture.enrolled = obj_ut.create_dummy_user()
    fixture.nobody = obj_ut.create_dummy_user()

    fixture.hidden_project = obj_ut.build_project(
        course_kwargs={'administrators': [fixture.admin]},
        semester_kwargs={
            'staff': [fixture.staff], 'enrolled_students': [fixture.enrolled]})

    fixture.semester = fixture.hidden_project.semester
    fixture.course = fixture.semester.course

    fixture.admin.courses_is_admin_for.add(fixture.course)
    fixture.staff.semesters_is_staff_for.add(fixture.semester)
    fixture.enrolled.semesters_is_enrolled_in.add(fixture.semester)

    fixture.visible_project = obj_ut.build_project(
        project_kwargs={'semester': fixture.semester,
                        'visible_to_students': True})

    fixture.course_url = reverse(
        'course:get', kwargs={'pk': fixture.course.pk})

    fixture.semester_url = reverse(
        'semester:get', kwargs={'pk': fixture.semester.pk})
    fixture.staff_url = reverse(
        'semester:staff', kwargs={'pk': fixture.semester.pk})
    fixture.enrolled_url = reverse(
        'semester:enrolled_students', kwargs={'pk': fixture.semester.pk})
    fixture.projects_url = reverse(
        'semester:projects', kwargs={'pk': fixture.semester.pk})

    fixture.hidden_project_url = reverse(
        'project:get', kwargs={'pk': fixture.hidden_project.pk})
    fixture.visible_project_url = reverse(
        'project:get', kwargs={'pk': fixture.visible_project.pk})

    fixture.visible_project_files_url = reverse(
        'project:files', kwargs={'pk': fixture.visible_project.pk})
    fixture.hidden_project_files_url = reverse(
        'project:files', kwargs={'pk': fixture.hidden_project.pk})


def _project_file_setup(fixture):
    fixture.file1 = SimpleUploadedFile('spam.cpp', b'asdkljflak;sdjf')
    fixture.file2 = SimpleUploadedFile('eggs.cpp', b'ajnvwurnvv')
    fixture.file1_url = reverse(
        'project:file',
        kwargs={'pk': fixture.visible_project.pk,
                'filename': fixture.file1.name})
    fixture.file2_url = reverse(
        'project:file',
        kwargs={'pk': fixture.visible_project.pk,
                'filename': fixture.file2.name})
    fixture.files_and_urls = sorted(
        zip(
            (fixture.file1, fixture.file2),
            (fixture.file1_url, fixture.file2_url)
        ), key=lambda pair: pair[0].name
    )

    fixture.visible_project.add_project_file(fixture.file1)
    fixture.visible_project.add_project_file(fixture.file2)


class GetUpdateProjectTestCase(TemporaryFilesystemTestCase):
    def setUp(self):
        super().setUp()

        _common_setup(self)

    def test_course_admin_or_semester_staff_get_visible_project(self):
        for user in self.admin, self.staff:
            client = MockClient(user)
            response = client.get(self.visible_project_url)

            self.assertEqual(200, response.status_code)
            expected_content = {
                "type": "project",
                "id": self.visible_project.pk,
                "name": self.visible_project.name,
                "visible_to_students": (
                    self.visible_project.visible_to_students),
                "closing_time": self.visible_project.closing_time,
                "disallow_student_submissions": (
                    self.visible_project.disallow_student_submissions),
                "allow_submissions_from_non_enrolled_students": (
                    (self.visible_project.
                        allow_submissions_from_non_enrolled_students)),
                "min_group_size": self.visible_project.min_group_size,
                "max_group_size": self.visible_project.max_group_size,
                "required_student_files": (
                    self.visible_project.required_student_files),
                "expected_student_file_patterns": (
                    self.visible_project.expected_student_file_patterns),
                "urls": {
                    "self": self.visible_project_url,
                    "semester": self.semester_url,
                    "uploaded_files": self.visible_project_files_url,
                }
            }

            self.assertEqual(
                expected_content, json_load_bytes(response.content))

    def test_course_admin_or_semester_staff_get_hidden_project(self):
        for user in self.admin, self.staff:
            client = MockClient(user)
            response = client.get(self.hidden_project_url)

            self.assertEqual(200, response.status_code)
            expected_content = {
                "type": "project",
                "id": self.hidden_project.pk,
                "name": self.hidden_project.name,
                "visible_to_students": (
                    self.hidden_project.visible_to_students),
                "closing_time": self.hidden_project.closing_time,
                "disallow_student_submissions": (
                    self.hidden_project.disallow_student_submissions),
                "allow_submissions_from_non_enrolled_students": (
                    (self.hidden_project.
                        allow_submissions_from_non_enrolled_students)),
                "min_group_size": self.hidden_project.min_group_size,
                "max_group_size": self.hidden_project.max_group_size,
                "required_student_files": (
                    self.hidden_project.required_student_files),
                "expected_student_file_patterns": (
                    self.hidden_project.expected_student_file_patterns),
                "urls": {
                    "self": self.hidden_project_url,
                    "semester": self.semester_url,
                    "uploaded_files": self.hidden_project_files_url,
                }
            }

            self.assertEqual(
                expected_content, json_load_bytes(response.content))

    def test_enrolled_student_or_other_get_hidden_project_permission_denied(self):
        for user in self.enrolled, self.nobody:
            client = MockClient(user)
            response = client.get(self.hidden_project_url)

            self.assertEqual(403, response.status_code)

    def test_enrolled_student_or_other_get_visible_public_project(self):
        self.visible_project.allow_submissions_from_non_enrolled_students = True
        self.visible_project.save()

        for user in self.enrolled, self.nobody:
            client = MockClient(user)
            response = client.get(self.visible_project_url)

            self.assertEqual(200, response.status_code)
            expected_content = {
                "type": "project",
                "id": self.visible_project.pk,
                "name": self.visible_project.name,
                "visible_to_students": (
                    self.visible_project.visible_to_students),
                "closing_time": self.visible_project.closing_time,
                "disallow_student_submissions": (
                    self.visible_project.disallow_student_submissions),
                "allow_submissions_from_non_enrolled_students": (
                    (self.visible_project.
                        allow_submissions_from_non_enrolled_students)),
                "min_group_size": self.visible_project.min_group_size,
                "max_group_size": self.visible_project.max_group_size,
                "required_student_files": (
                    self.visible_project.required_student_files),
                "expected_student_file_patterns": (
                    self.visible_project.expected_student_file_patterns),
                "urls": {
                    "self": self.visible_project_url,
                    "semester": self.semester_url,
                    "uploaded_files": self.visible_project_files_url,
                }
            }

            self.assertEqual(
                expected_content, json_load_bytes(response.content))

    def test_other_get_visible_non_public_project_permission_denied(self):
        client = MockClient(self.nobody)
        response = client.get(self.visible_project_url)
        self.assertEqual(403, response.status_code)

    # -------------------------------------------------------------------------

    def test_course_admin_edit_some_project_fields(self):
        edits = {
            'name': 'spaaaaam',
            'max_group_size': 4,
            'visible_to_students': True
        }

        client = MockClient(self.admin)
        response = client.patch(self.hidden_project_url, edits)
        self.assertEqual(204, response.status_code)

        loaded = Project.objects.get(pk=self.hidden_project.pk)
        for field_name, value in edits.items():
            self.assertEqual(value, getattr(loaded, field_name))

    def test_course_admin_edit_all_project_fields(self):
        edits = {
            "name": 'spam test',
            "visible_to_students": True,
            "closing_time": timezone.now().replace(microsecond=0),
            "disallow_student_submissions": True,
            "allow_submissions_from_non_enrolled_students": True,
            "min_group_size": 2,
            "max_group_size": 3,
            "required_student_files": ['spam', 'egg'],
            "expected_student_file_patterns": [
                {
                    "pattern": 'test_*.cpp',
                    "min_num_matches": 1,
                    "max_num_matches": 5
                }
            ]
        }

        client = MockClient(self.admin)
        response = client.patch(self.hidden_project_url, edits)
        self.assertEqual(204, response.status_code)

        edits['expected_student_file_patterns'] = [
            Project.FilePatternTuple(
                obj['pattern'], obj['min_num_matches'], obj['max_num_matches']
            )
            for obj in edits['expected_student_file_patterns']
        ]

        loaded = Project.objects.get(pk=self.hidden_project.pk)
        for field_name, value in edits.items():
            self.assertEqual(value, getattr(loaded, field_name))

    def test_edit_project_invalid_settings(self):
        bad_edits = {
            'min_group_size': 3,
            'max_group_size': 2
        }

        client = MockClient(self.admin)
        response = client.patch(self.hidden_project_url, bad_edits)
        self.assertEqual(400, response.status_code)

        loaded = Project.objects.get(pk=self.hidden_project.pk)
        self.assertNotEqual(loaded.min_group_size, bad_edits['min_group_size'])
        self.assertNotEqual(loaded.max_group_size, bad_edits['max_group_size'])

    def test_other_edit_project_permission_denied(self):
        original_name = self.visible_project.name
        for user in self.staff, self.enrolled, self.nobody:
            client = MockClient(user)
            response = client.patch(
                self.visible_project_url, {'name': 'cheese'})
            self.assertEqual(403, response.status_code)

            loaded = Project.objects.get(pk=self.visible_project.pk)
            self.assertEqual(original_name, loaded.name)

# -----------------------------------------------------------------------------
# -----------------------------------------------------------------------------


class ListAddProjectFileTestCase(TemporaryFilesystemTestCase):
    def setUp(self):
        super().setUp()

        _common_setup(self)
        _project_file_setup(self)

    def test_course_admin_or_semester_staff_list_files(self):
        for user in self.admin, self.staff:
            client = MockClient(user)
            response = client.get(self.visible_project_files_url)
            self.assertEqual(200, response.status_code)

            expected_content = {
                "uploaded_files": [
                    {
                        "filename": file_.name,
                        "size": file_.size,
                        "url": url
                    }
                    for file_, url in self.files_and_urls
                ]
            }

            self.assertEqual(
                expected_content, json_load_bytes(response.content))

    def test_other_list_files_permission_denied(self):
        for user in self.enrolled, self.nobody:
            client = MockClient(user)
            response = client.get(self.visible_project_files_url)
            self.assertEqual(403, response.status_code)

    # -------------------------------------------------------------------------

    def test_course_admin_add_files(self):
        good_files = [
            SimpleUploadedFile('new_file1.txt', b'cauisdiaugw'),
            SimpleUploadedFile('new_file2.txt', b'ancjdweiua')
        ]
        bad_files = [
            SimpleUploadedFile('../bad_filename; echo "blah" #', b'merp'),
        ]

        client = MockClient(self.admin)
        response = client.post(
            self.visible_project_files_url, {'files': good_files + bad_files},
            encode_data=False)

        self.assertEqual(200, response.status_code)

        expected_success_content = [
            {
                'filename': file_.name,
                'size': file_.size,
                'url': reverse(
                    'project:file',
                    kwargs={
                        'pk': self.visible_project.pk,
                        'filename': file_.name})
            }
            for file_ in good_files
        ]

        actual_content = json_load_bytes(response.content)
        self.assertEqual(expected_success_content, actual_content['success'])

        self.assertEqual(1, len(actual_content['failure']))
        self.assertTrue('error_message' in actual_content['failure'][0])
        self.assertEqual(
            bad_files[0].name, actual_content['failure'][0]['filename'])

    def test_other_add_files_permission_denied(self):
        data = {
            'files': [SimpleUploadedFile('new_file1.txt', b'cauisdiaugw')]
        }
        for user in self.staff, self.enrolled, self.nobody:
            client = MockClient(user)
            response = client.post(
                self.visible_project_files_url, data, encode_data=False)
            self.assertEqual(403, response.status_code)

# -----------------------------------------------------------------------------
# -----------------------------------------------------------------------------


class GetUpdateDeleteProjectFileTestCase(TemporaryFilesystemTestCase):
    def setUp(self):
        super().setUp()

        _common_setup(self)
        _project_file_setup(self)

    def test_course_admin_or_semester_staff_get_file(self):
        for user in self.admin, self.staff:
            client = MockClient(user)
            response = client.get(self.file2_url)

            self.assertEqual(200, response.status_code)

            self.file2.seek(0)
            expected_content = {
                "type": "project_file",
                "filename": self.file2.name,
                "size": self.file2.size,
                "content": self.file2.read().decode('utf-8'),
                "urls": {
                    "self": self.file2_url,
                    "project": self.visible_project_url
                }
            }

            self.assertEqual(
                expected_content, json_load_bytes(response.content))

    def test_other_get_file_permission_denied(self):
        for user in self.enrolled, self.nobody:
            client = MockClient(user)
            response = client.get(self.file2_url)

            self.assertEqual(403, response.status_code)

    def test_course_admin_edit_file(self):
        edits = {
            # 'filename': 'new_name.txt', # TODO
            'content': 'new contents'
        }
        client = MockClient(self.admin)
        response = client.patch(self.file1_url, edits)

        self.assertEqual(200, response.status_code)

        expected_content = {
            'size': self.visible_project.get_file(self.file1.name).size
        }

        self.assertEqual(expected_content, json_load_bytes(response.content))

        loaded_file = self.visible_project.get_file(self.file1.name)
        # self.assertEqual(loaded_file.name, edits['filename'])
        self.assertEqual(loaded_file.read(), edits['content'])

    def test_other_edit_file_permission_denied(self):
        for user in self.staff, self.enrolled, self.nobody:
            client = MockClient(user)
            response = client.patch(self.file1_url, {'name': 'blaaaah'})
            self.assertEqual(403, response.status_code)

            loaded_file = self.visible_project.get_file(self.file1.name)
            self.assertEqual(self.file1.name, loaded_file.name)

    # -------------------------------------------------------------------------

    def test_course_admin_delete_file(self):
        client = MockClient(self.admin)
        response = client.delete(self.file1_url)
        self.assertEqual(204, response.status_code)

        self.visible_project = Project.objects.get(pk=self.visible_project.pk)

        with self.assertRaises(ObjectDoesNotExist):
            self.visible_project.get_file(self.file1.name)

    def test_other_delete_file_permission_denied(self):
        for user in self.staff, self.enrolled, self.nobody:
            client = MockClient(user)
            response = client.delete(self.file1_url)
            self.assertEqual(403, response.status_code)

            self.visible_project.get_file(self.file1.name)

# -----------------------------------------------------------------------------
# -----------------------------------------------------------------------------


class ListAddAutograderTestCaseEndpointTestCase(TemporaryFilesystemTestCase):
    def setUp(self):
        super().setUp()

        self.maxDiff = None

        _common_setup(self)

        self.visible_project.required_student_files = ['spam.cpp']
        self.visible_project.validate_and_save()

        self.ag_test1 = AutograderTestCaseFactory.validate_and_create(
            'compiled_and_run_test_case',
            name='test1',
            compiler='g++',
            student_resource_files=self.visible_project.required_student_files,
            student_files_to_compile_together=self.visible_project.required_student_files,
            project=self.visible_project
        )
        self.ag_test2 = AutograderTestCaseFactory.validate_and_create(
            'compilation_only_test_case',
            name='test2',
            compiler='g++',
            student_resource_files=self.visible_project.required_student_files,
            student_files_to_compile_together=self.visible_project.required_student_files,
            project=self.visible_project
        )

        self.ag_tests_url = reverse(
            'project:ag-tests', kwargs={'pk': self.visible_project.pk})

    def test_course_admin_or_semester_staff_list_tests(self):
        for user in self.admin, self.staff:
            client = MockClient(user)
            response = client.get(self.ag_tests_url)
            self.assertEqual(200, response.status_code)
            expected_content = {
                'autograder_test_cases': [
                    {
                        'name': test.name,
                        'url': reverse('ag-test:get', kwargs={'pk': test.pk})
                    }
                    for test in sorted(
                        (self.ag_test1, self.ag_test2),
                        key=lambda obj: obj.name)
                ]
            }

            actual_content = json_load_bytes(response.content)
            actual_content['autograder_test_cases'].sort(
                key=lambda obj: obj['name'])
            self.assertEqual(
                expected_content, actual_content)

    def test_other_list_tests_permission_denied(self):
        for user in self.enrolled, self.nobody:
            client = MockClient(user)
            response = client.get(self.ag_tests_url)
            self.assertEqual(403, response.status_code)

    # -------------------------------------------------------------------------

    def test_course_admin_add_test(self):
        name = 'spam'
        type_str = 'compiled_and_run_test_case'
        client = MockClient(self.admin)
        response = client.post(
            self.ag_tests_url,
            {'name': name, 'type': type_str, 'compiler': 'g++',
             'student_resource_files': (
                 self.visible_project.required_student_files),
             'student_files_to_compile_together': (
                 self.visible_project.required_student_files)})

        self.assertEqual(201, response.status_code)

        loaded = AutograderTestCaseBase.objects.get(name=name)
        self.assertEqual('g++', loaded.compiler)
        self.assertEqual(
            self.visible_project.required_student_files,
            loaded.student_files_to_compile_together)

        expected_content = {
            'name': name,
            'type': type_str,
            'url': reverse('ag-test:get', kwargs={'pk': loaded.pk})
        }

        self.assertEqual(
            expected_content, json_load_bytes(response.content))

    def test_other_add_test_permission_denied(self):
        name = 'cheese'
        for user in self.staff, self.enrolled, self.nobody:
            client = MockClient(user)
            response = client.post(
                self.ag_tests_url,
                {'name': name, 'type': 'compiled_and_run_test_case',
                 'compiler': 'g++',
                 'student_files_to_compile_together': (
                     self.visible_project.required_student_files)})
            self.assertEqual(403, response.status_code)

            with self.assertRaises(ObjectDoesNotExist):
                AutograderTestCaseBase.objects.get(name=name)

    def test_add_test_invalid_settings(self):
        name = 'testy'
        client = MockClient(self.admin)
        response = client.post(
            self.ag_tests_url,
            {'name': name, 'type': 'compiled_and_run_test_case',
             'compiler': 'not_a_compiler'})

        self.assertEqual(400, response.status_code)

        with self.assertRaises(ObjectDoesNotExist):
            AutograderTestCaseBase.objects.get(name=name)

    def test_add_test_invalid_test_type(self):
        name = 'testy'
        client = MockClient(self.admin)
        response = client.post(
            self.ag_tests_url,
            {'name': name, 'type': 'not_a_test_type'})

        self.assertEqual(400, response.status_code)

        with self.assertRaises(ObjectDoesNotExist):
            AutograderTestCaseBase.objects.get(name=name)

# -----------------------------------------------------------------------------
# -----------------------------------------------------------------------------


class ListAddStudentTestSuiteTestCase(TemporaryFilesystemTestCase):
    def setUp(self):
        super().setUp()

        _common_setup(self)

        self.visible_project.expected_student_file_patterns = [
            Project.FilePatternTuple('test_*.cpp', 1, 3)
        ]
        self.visible_project.validate_and_save()
        self.correct_impl_file = SimpleUploadedFile('blah', b'aasdjfasdf')
        self.visible_project.add_project_file(self.correct_impl_file)

        self.suite1 = StudentTestSuiteFactory.validate_and_create(
            'compiled_student_test_suite',
            name='suite1',
            compiler='clang',
            project=self.visible_project,
            student_test_case_filename_pattern=(
                self.visible_project.expected_student_file_patterns[0].pattern
            ),
            correct_implementation_filename=self.correct_impl_file.name
        )
        self.suite2 = StudentTestSuiteFactory.validate_and_create(
            'compiled_student_test_suite',
            name='suite2',
            compiler='clang',
            project=self.visible_project,
            student_test_case_filename_pattern=(
                self.visible_project.expected_student_file_patterns[0].pattern),
            correct_implementation_filename=self.correct_impl_file.name
        )

        self.suites_url = reverse(
            'project:suites', kwargs={'pk': self.visible_project.pk})

    def test_course_admin_or_semester_staff_list_suites(self):
        for user in self.admin, self.staff:
            client = MockClient(user)
            response = client.get(self.suites_url)

            self.assertEqual(200, response.status_code)

            expected_content = {
                "student_test_suites": [
                    {
                        'name': suite.name,
                        'url': reverse('suite:get', kwargs={'pk': suite.pk})
                    }
                    for suite in sorted(
                        (self.suite1, self.suite2),
                        key=lambda obj: obj.name)
                ]
            }

            actual_content = json_load_bytes(response.content)
            actual_content['student_test_suites'].sort(
                key=lambda obj: obj['name'])
            self.assertEqual(expected_content, actual_content)

    def test_other_list_suites_permission_denied(self):
        for user in self.enrolled, self.nobody:
            client = MockClient(user)
            response = client.get(self.suites_url)

            self.assertEqual(403, response.status_code)

    def test_course_admin_add_suite(self):
        args = {
            'type': 'compiled_student_test_suite',
            'name': 'suite3',
            'compiler': 'gcc',
            'student_test_case_filename_pattern': (
                self.visible_project.expected_student_file_patterns[0].pattern),
            'correct_implementation_filename': self.correct_impl_file.name
        }

        client = MockClient(self.admin)
        response = client.post(self.suites_url, args)

        self.assertEqual(201, response.status_code)

        loaded = StudentTestSuiteBase.objects.get(name=args['name'])

        expected_content = {
            "type": args['type'],
            "name": args['name'],
            "url": reverse('suite:get', kwargs={'pk': loaded.pk})
        }

        self.assertEqual(expected_content, json_load_bytes(response.content))

        self.assertEqual(args.pop('type'), loaded.get_type_str())
        for key, value in args.items():
            self.assertEqual(value, getattr(loaded, key))

    def test_other_add_suite_permission_denied(self):
        args = {
            'type': 'compiled_student_test_suite',
            'name': 'suite3',
            'student_test_case_filename_pattern': (
                self.visible_project.expected_student_file_patterns[0].pattern),
            'correct_implementation_filename': self.correct_impl_file.name,
        }
        for user in self.staff, self.enrolled, self.nobody:
            client = MockClient(user)
            response = client.post(self.suites_url, {'name': args['name']})
            self.assertEqual(403, response.status_code)

            with self.assertRaises(ObjectDoesNotExist):
                StudentTestSuiteBase.objects.get(name=args['name'])

    def test_add_suite_invalid_settings(self):
        args = {
            'type': 'compiled_student_test_suite',
            'name': 'suite3',
            'student_test_case_filename_pattern': (
                self.visible_project.expected_student_file_patterns[0].pattern
            ),
            'correct_implementation_filename': self.correct_impl_file.name,
            'compiler': 'not_a_compiler'
        }

        client = MockClient(self.admin)
        response = client.post(self.suites_url, args)

        self.assertEqual(400, response.status_code)

        with self.assertRaises(ObjectDoesNotExist):
            StudentTestSuiteBase.objects.get(name=args['name'])

    def test_add_suite_invalid_suite_type(self):
        args = {
            'type': 'not_a_type',
            'name': 'suite3',
            'student_test_case_filename_pattern': (
                self.visible_project.expected_student_file_patterns[0].pattern
            ),
            'correct_implementation_filename': self.correct_impl_file.name,
        }

        client = MockClient(self.admin)
        response = client.post(self.suites_url, args)

        self.assertEqual(400, response.status_code)

        with self.assertRaises(ObjectDoesNotExist):
            StudentTestSuiteBase.objects.get(name=args['name'])

# -----------------------------------------------------------------------------
# -----------------------------------------------------------------------------


class ListAddSubmissionGroupTestCase(TemporaryFilesystemTestCase):
    def setUp(self):
        super().setUp()

        _common_setup(self)

    def _add_groups_to_project(self, project, num_groups):
        return [
            obj_ut.build_submission_group(
                group_kwargs={'project': project})
            for i in range(num_groups)
        ]

    def _get_groups_url(self, project):
        return reverse('project:groups', kwargs={'pk': project.pk})

    def test_course_admin_or_semester_staff_list_default_page_size(self):
        groups = self._add_groups_to_project(self.visible_project, 35)

        for user in self.admin, self.staff:
            client = MockClient(user)
            response = client.get(self._get_groups_url(self.visible_project))
            self.assertEqual(200, response.content)

            expected_content = {
                'user_submission_group': None,
                'submission_groups': [
                    {
                        'members': [
                            member.username for member in group.member_names],
                        'url': reverse('group:get', kwargs={'pk': group.pk})
                    }
                    for group in groups[:DEFAULT_SUBMISSION_GROUP_PAGE_SIZE]
                ],
                'total_num_submission_groups': len(groups)
            }

            self.assertEqual(
                expected_content, json_load_bytes(response.content))

    def test_course_admin_or_semester_staff_list_first_page_custom_page_size(self):
        groups = self._add_groups_to_project(self.visible_project, 5)

        page_size = 2
        page_num = 0
        for user in self.admin, self.staff:
            client = MockClient(user)
            response = client.get(
                self._get_groups_url(self.visible_project),
                {'page_size': page_size, 'page_num': page_num})
            self.assertEqual(200, response.content)

            expected_content = {
                'user_submission_group': None,
                'submission_groups': [
                    {
                        'members': [
                            member.username for member in group.member_names],
                        'url': reverse('group:get', kwargs={'pk': group.pk})
                    }
                    for group in groups[
                        page_num * page_size:(page_num + 1) * page_size]
                ],
                'total_num_submission_groups': len(groups)
            }

            self.assertEqual(
                expected_content, json_load_bytes(response.content))

    def test_course_admin_or_semester_staff_list_middle_page_custom_page_size(self):
        groups = self._add_groups_to_project(self.visible_project, 5)

        page_size = 2
        page_num = 1
        for user in self.admin, self.staff:
            client = MockClient(user)
            response = client.get(
                self._get_groups_url(self.visible_project),
                {'page_size': page_size, 'page_num': page_num})
            self.assertEqual(200, response.content)

            expected_content = {
                'user_submission_group': None,
                'submission_groups': [
                    {
                        'members': [
                            member.username for member in group.member_names],
                        'url': reverse('group:get', kwargs={'pk': group.pk})
                    }
                    for group in groups[
                        page_num * page_size:(page_num + 1) * page_size]
                ],
                'total_num_submission_groups': len(groups)
            }

            self.assertEqual(
                expected_content, json_load_bytes(response.content))

    def test_course_admin_or_semester_staff_list_last_page_custom_page_size(self):
        groups = self._add_groups_to_project(self.visible_project, 5)

        page_size = 2
        page_num = 2
        for user in self.admin, self.staff:
            client = MockClient(user)
            response = client.get(
                self._get_groups_url(self.visible_project),
                {'page_size': page_size, 'page_num': page_num})
            self.assertEqual(200, response.content)

            expected_content = {
                'user_submission_group': None,
                'submission_groups': [
                    {
                        'members': [
                            member.username for member in group.member_names],
                        'url': reverse('group:get', kwargs={'pk': group.pk})
                    }
                    for group in groups[
                        page_num * page_size:]
                ],
                'total_num_submission_groups': len(groups)
            }

            self.assertEqual(
                expected_content, json_load_bytes(response.content))

    def test_course_admin_or_semester_staff_filter_groups(self):
        groups = self._add_groups_to_project(self.visible_project, 5)
        self.enrolled.username = 'steve'
        self.enrolled.save()
        other_member = obj_ut.create_dummy_user()
        other_member.semesters_is_enrolled_in.add(
            self.visible_project.semester)
        group_to_find = obj_ut.build_submission_group(
            group_kwargs={'members': [self.enrolled.username, other_member],
                          'project': self.visible_project})

        for user in self.admin, self.staff:
            client = MockClient(user)
            response = client.get(
                self._get_groups_url(self.visible_project),
                {'group_contains': [
                    self.enrolled.username, other_member.username]})

            self.assertEqual(200, response.status_code)

            expected_content = {
                'user_submission_group': None,
                'submission_groups': [
                    {
                        'members': [
                            member.username for member in
                            group_to_find.member_names],
                        'url': reverse(
                            'group:get', kwargs={'pk': group_to_find.pk})
                    }
                ],
                'total_num_submission_groups': len(groups)
            }

            self.assertEqual(
                expected_content, json_load_bytes(response.content))

    def test_enrolled_student_in_submission_group_list_groups(self):
        self._add_groups_to_project(self.visible_project, 5)
        user_group = obj_ut.build_submission_group(
            group_kwargs={'members': [self.enrolled.username],
                          'project': self.visible_project})

        client = MockClient(self.enrolled)
        response = client.get(self._get_groups_url(self.visible_project))

        self.assertEqual(200, response.status_code)

        expected_content = {
            'user_submission_group': {
                'members': [self.enrolled.username],
                'url': reverse(
                    'group:get', kwargs={'pk': user_group.pk})

            }
        }

        self.assertEqual(expected_content, json_load_bytes(response.content))

    def test_non_enrolled_student_public_project_list_groups(self):
        self.visible_project.allow_submissions_from_non_enrolled_students = True
        self.visible_project.validate_and_save()

        user_group = obj_ut.build_submission_group(
            group_kwargs={'members': [self.nobody.username],
                          'project': self.visible_project})

        client = MockClient(self.nobody)
        response = client.get(self._get_groups_url(self.visible_project))

        self.assertEqual(200, response.status_code)

        expected_content = {
            'user_submission_group': {
                'members': [self.nobody.username],
                'url': reverse(
                    'group:get', kwargs={'pk': user_group.pk})

            }
        }

        self.assertEqual(expected_content, json_load_bytes(response.content))

    def test_student_not_in_group_public_visible_project(self):
        self.visible_project.allow_submissions_from_non_enrolled_students = True
        self.visible_project.validate_and_save()

        for user in self.enrolled, self.nobody:
            client = MockClient(user)
            response = client.get(self._get_groups_url(self.visible_project))
            self.assertEqual(200, response.status_code)

            self.assertEqual({'user_submission_group': None},
                             json_load_bytes(response.content))

    def test_student_list_groups_hidden_project_permission_denied(self):
        self.hidden_project.allow_submissions_from_non_enrolled_students = True
        self.hidden_project.validate_and_save()

        for user in self.enrolled, self.nobody:
            client = MockClient(user)
            response = client.get(self._get_groups_url(self.hidden_project))
            self.assertEqual(403, response.status_code)

    def test_list_groups_non_enrolled_student_private_project_permission_denied(self):
        self.visible_project.allow_submissions_from_non_enrolled_students = True
        self.visible_project.validate_and_save()

        client = MockClient(self.nobody)
        response = client.get(self._get_groups_url(self.visible_project))
        self.assertEqual(403, response.status_code)

    # -------------------------------------------------------------------------

    def test_course_admin_create_group_of_others(self):
        num_members = 3
        members = obj_ut.create_dummy_users(num_members)
        member_names = [member.username for member in members]
        self.hidden_project.max_group_size = num_members
        self.hidden_project.validate_and_save

        client = MockClient(self.admin)
        response = client.post(
            self._get_groups_url(self.hidden_project),
            {'members': member_names})

        self.assertEqual(201, response.status_code)

        loaded = SubmissionGroup.get_group(members[0], self.hidden_project)
        self.assertCountEqual(member_names, loaded.member_names)

        expected_content = {
            'members': member_names,
            'url': reverse('group:get', kwargs={'pk': loaded.pk})
        }

        self.assertEqual(expected_content, json_load_bytes(response.content))

    def test_course_admin_create_group_of_others_users_dont_exist_yet(self):
        member_names = ['steve', 'joe']
        self.hidden_project.max_group_size = len(member_names)
        self.hidden_project.validate_and_save

        client = MockClient(self.admin)
        response = client.post(
            self._get_groups_url(self.hidden_project),
            {'members': member_names})

        self.assertEqual(201, response.status_code)

        members = [
            User.objects.get(username=username)
            for username in member_names
        ]

        loaded = SubmissionGroup.get_group(members[0], self.hidden_project)
        self.assertCountEqual(member_names, loaded.member_names)

        expected_content = {
            'members': member_names,
            'url': reverse('group:get', kwargs={'pk': loaded.pk})
        }

        self.assertEqual(expected_content, json_load_bytes(response.content))

    def test_course_admin_create_group_of_others_override_max_size(self):
        member_names = ['steve', 'joe']
        self.hidden_project.max_group_size = 1
        self.hidden_project.validate_and_save

        client = MockClient(self.admin)
        response = client.post(
            self._get_groups_url(self.hidden_project),
            {'members': member_names})

        self.assertEqual(201, response.status_code)

        members = [
            User.objects.get(username=username)
            for username in member_names
        ]

        loaded = SubmissionGroup.get_group(members[0], self.hidden_project)
        self.assertCountEqual(member_names, loaded.member_names)

        expected_content = {
            'members': member_names,
            'url': reverse('group:get', kwargs={'pk': loaded.pk})
        }

        self.assertEqual(expected_content, json_load_bytes(response.content))

    def test_course_admin_create_group_of_others_override_min_size(self):
        member_names = ['steve', 'joe']
        self.hidden_project.min_group_size = 3
        self.hidden_project.max_group_size = 3
        self.hidden_project.validate_and_save

        client = MockClient(self.admin)
        response = client.post(
            self._get_groups_url(self.hidden_project),
            {'members': member_names})

        self.assertEqual(201, response.status_code)

        members = [
            User.objects.get(username=username)
            for username in member_names
        ]

        loaded = SubmissionGroup.get_group(members[0], self.hidden_project)
        self.assertCountEqual(member_names, loaded.member_names)

        expected_content = {
            'members': member_names,
            'url': reverse('group:get', kwargs={'pk': loaded.pk})
        }

        self.assertEqual(expected_content, json_load_bytes(response.content))

    def test_course_admin_create_group_error_group_size_zero(self):
        client = MockClient(self.admin)
        response = client.post(
            self._get_groups_url(self.hidden_project), {'members': []})

        self.assertEqual(400, response.status_code)

    def test_student_create_group_with_only_self(self):
        self.visible_project.allow_submissions_from_non_enrolled_students = True
        self.visible_project.validate_and_save()
        for user in self.enrolled, self.nobody:
            client = MockClient(user)

            response = client.post(
                self._get_groups_url(self.visible_project),
                {'members': [user.username]})
            self.assertEqual(201, response.status_code)

            loaded = SubmissionGroup.get_group(user, self.visible_project)
            self.assertEqual([user.username], loaded.member_names)

    def test_error_student_create_group_with_only_self_but_min_group_size_2(self):
        self.visible_project.allow_submissions_from_non_enrolled_students = True
        self.visible_project.min_group_size = 2
        self.visible_project.max_group_size = 2
        self.visible_project.validate_and_save()

        for user in self.enrolled, self.nobody:
            client = MockClient(user)

            response = client.post(
                self._get_groups_url(self.visible_project),
                {'members': [user.username]})
            self.assertEqual(400, response.status_code)

            with self.assertRaises(ObjectDoesNotExist):
                SubmissionGroup.get_group(user, self.visible_project)

    def test_student_create_group_with_only_self_hidden_project_permission_denied(self):
        self.hidden_project.allow_submissions_from_non_enrolled_students = True
        self.hidden_project.validate_and_save()

        for user in self.enrolled, self.nobody:
            client = MockClient(user)

            response = client.post(
                self._get_groups_url(self.hidden_project),
                {'members': [user.username]})
            self.assertEqual(403, response.status_code)

            with self.assertRaises(ObjectDoesNotExist):
                SubmissionGroup.get_group(user, self.hidden_project)

    def test_student_create_multiple_member_group_permission_denied(self):
        self.visible_project.allow_submissions_from_non_enrolled_students = True
        self.visible_project.min_group_size = 2
        self.visible_project.max_group_size = 2
        self.visible_project.validate_and_save()

        other_enrolled = obj_ut.create_dummy_user()
        other_enrolled.semesters_is_enrolled_in.add(self.visible_project.semester)

        other_nobody = obj_ut.create_dummy_user()

        enrolled_members = [self.enrolled.username, other_enrolled.username]
        non_enrolled_members = [self.nobody.username, other_nobody.username]

        iterable = zip((self.enrolled, self.nobody),
                       (enrolled_members, non_enrolled_members))
        for user, members in iterable:
            client = MockClient(user)
            response = client.post(
                self._get_groups_url(self.visible_project),
                {'members': members})

            self.assertEqual(403, response.status_code)

            with self.assertRaises(ObjectDoesNotExist):
                SubmissionGroup.get_group(user, self.visible_project)

    def test_non_enrolled_student_create_group_with_only_self_non_public_project_permission_denied(self):
        self.visible_project.allow_submissions_from_non_enrolled_students = False
        self.visible_project.validate_and_save()

        client = MockClient(self.nobody)
        response = client.post(
            self._get_groups_url(self.visible_project),
            {'members': [self.nobody.username]})
        self.assertEqual(403, response.status_code)

        with self.assertRaises(ObjectDoesNotExist):
            SubmissionGroup.get_group(self.nobody, self.visible_project)

    def test_error_user_already_in_group(self):
        SubmissionGroup.objects.validate_and_create(
            members=[self.enrolled.username], project=self.visible_project)

        for user in self.admin, self.enrolled:
            client = MockClient(user)
            response = client.post(
                self._get_groups_url(self.visible_project),
                {'members': [self.enrolled.username]})
            self.assertEqual(400, response.status_code)

# -----------------------------------------------------------------------------
# -----------------------------------------------------------------------------


class ListAddSubmissionGroupInvitationTestCase(TemporaryFilesystemTestCase):
    def setUp(self):
        super().setUp()

        _common_setup(self)

        self.admin_invitee = obj_ut.create_dummy_user()
        self.admin_invitee.courses_is_admin_for.add(self.course)
        self.staff_invitee = obj_ut.create_dummy_user()
        self.staff_invitee.semesters_is_staff_for.add(self.semester)
        self.enrolled_invitee = obj_ut.create_dummy_user()
        self.enrolled_invitee.semesters_is_enrolled_in.add(self.semester)
        self.nobody_invitee = obj_ut.create_dummy_user()

        self.visible_project.min_group_size = 2
        self.visible_project.max_group_size = 2
        self.visible_project.validate_and_save()

        self.hidden_project.min_group_size = 2
        self.hidden_project.max_group_size = 2
        self.hidden_project.validate_and_save()

    def _get_invitations_url(self, project):
        return reverse('project:invitations', kwargs={'pk': project.pk})

    def test_all_user_types_list_group_invitations(self):
        self.visible_project.allow_submissions_from_non_enrolled_students = True
        self.visible_project.validate_and_save()

        iterable = zip(
            (self.admin, self.staff, self.staff, self.enrolled, self.nobody),
            (self.admin_invitee, self.staff_invitee, self.admin_invitee,
             self.enrolled_invitee, self.nobody_invitee)
        )
        for invitor, invitee in iterable:
            invitations_sent = [
                SubmissionGroupInvitation.objects.validate_and_create(
                    invited_users=[invitee.username],
                    invitation_creator=invitor.username,
                    project=self.visible_project)
                for i in range(2)
            ]
            invitations_received = [
                SubmissionGroupInvitation.objects.validate_and_create(
                    invited_users=[invitor.username],
                    invitation_creator=invitee.username,
                    project=self.visible_project)
                for i in range(2)
            ]

            client = MockClient(invitor)
            response = client.get(
                self._get_invitations_url(self.visible_project))
            self.assertEqual(200, response.status_code)

            expected_content = {
                'invitations_sent': [
                    {
                        'users_invited': [invitation_sent.invited_usernames],
                        'url': reverse(
                            'invitations:get',
                            kwargs={'pk': invitation_sent.pk})
                    }
                    for invitation_sent in invitations_sent
                ],
                'invitations_received': [
                    {
                        'invitation_creator': (
                            invitation_received.invitation_creator.username),
                        'url': reverse('invitations:get',
                                       kwargs={'pk': invitation_received.pk})
                    }
                    for invitation_received in invitations_received
                ]
            }

            self.assertEqual(
                expected_content, json_load_bytes(response.content))

    def test_student_list_group_invitations_hidden_project_permission_denied(self):
        self.hidden_project.allow_submissions_from_non_enrolled_students = True
        self.hidden_project.validate_and_save()
        iterable = zip(
            (self.enrolled, self.nobody),
            (self.enrolled_invitee, self.nobody_invitee)
        )
        for invitor, invitee in iterable:
            client = MockClient(invitor)
            response = client.get(
                self._get_invitations_url(self.hidden_project))
            self.assertEqual(403, response.status_code)

    def test_non_enrolled_student_non_public_project_list_group_invitations_permission_denied(self):
        self.hidden_project.allow_submissions_from_non_enrolled_students = False
        self.hidden_project.validate_and_save()

        client = MockClient(self.nobody)
        response = client.get(
            self._get_invitations_url(self.hidden_project))
        self.assertEqual(403, response.status_code)

    # -------------------------------------------------------------------------

    def test_valid_all_user_types_create_group_invitation(self):
        self.visible_project.allow_submissions_from_non_enrolled_students = True
        self.visible_project.validate_and_save()

        iterable = zip(
            (self.admin, self.staff, self.staff, self.enrolled, self.nobody),
            (self.admin_invitee, self.staff_invitee, self.admin_invitee,
             self.enrolled_invitee, self.nobody_invitee)
        )
        for invitor, invitee in iterable:
            client = MockClient(invitor)
            response = client.post(
                self._get_invitations_url(self.visible_project),
                {'users_to_invite': [invitee.username]})
            self.assertEqual(201, response.status_code)

            loaded = SubmissionGroupInvitation.objects.get(
                invitation_creator=invitor)

            self.assertEqual([invitee.username], loaded.invited_usernames)

            expected_content = {
                'invitation_creator': invitor.username,
                'url': reverse('invitations:get', kwargs={'pk': loaded.pk})
            }

            self.assertEqual(
                expected_content, json_load_bytes(response.content))

            self.assertEqual(1, invitee.notifications.count())

    def test_student_create_invitation_hidden_project_permission_denied(self):
        self.hidden_project.allow_submissions_from_non_enrolled_students = True
        self.hidden_project.validate_and_save()

        iterable = zip(
            (self.enrolled, self.nobody),
            (self.enrolled_invitee, self.nobody_invitee)
        )

        for invitor, invitee in iterable:
            client = MockClient(invitor)
            response = client.post(
                self._get_invitations_url(self.hidden_project),
                {'users_to_invite': [invitee.username]})
            self.assertEqual(403, response.status_code)

            with self.assertRaises(ObjectDoesNotExist):
                SubmissionGroupInvitation.objects.get(
                    invitation_creator=invitor)

    def test_non_enrolled_student_non_public_project_create_invitation_permission_denied(self):
        client = MockClient(self.nobody)
        response = client.post(
            self._get_invitations_url(self.visible_project),
            {'users_to_invite': [self.nobody_invitee.username]})
        self.assertEqual(403, response.status_code)

        with self.assertRaises(ObjectDoesNotExist):
            SubmissionGroupInvitation.objects.get(
                invitation_creator=self.nobody)

    def test_error_create_group_invitation_no_invited_users(self):
        self.visible_project.allow_submissions_from_non_enrolled_students = True
        self.visible_project.min_group_size = 1
        self.visible_project.max_group_size = 1
        self.visible_project.validate_and_save()

        for invitor in self.admin, self.staff, self.enrolled, self.nobody:
            client = MockClient(invitor)
            response = client.post(
                self._get_invitations_url(self.visible_project),
                {'users_to_invite': []})
            self.assertEqual(400, response.status_code)

            self.assertEqual(0, invitor.group_invitations_sent.count())

    def test_error_create_invitation_with_enrolled_and_non_enrolled(self):
        self.visible_project.allow_submissions_from_non_enrolled_students = True
        self.visible_project.validate_and_save()

        client = MockClient(self.enrolled)
        response = client.post(
            self._get_invitations_url(self.visible_project),
            {'users_to_invite': [self.nobody_invitee.username]})

        self.assertEqual(400, response.status_code)
        with self.assertRaises(ObjectDoesNotExist):
            SubmissionGroupInvitation.objects.get(
                invitation_creator=self.enrolled)

    def test_error_maximum_group_size_is_one(self):
        self.visible_project.allow_submissions_from_non_enrolled_students = True
        self.visible_project.min_group_size = 1
        self.visible_project.max_group_size = 1
        self.visible_project.validate_and_save()

        iterable = zip(
            (self.admin, self.staff, self.staff, self.enrolled, self.nobody),
            (self.admin_invitee, self.staff_invitee, self.admin_invitee,
             self.enrolled_invitee, self.nobody_invitee)
        )
        for invitor, invitee in iterable:
            client = MockClient(invitor)
            response = client.post(
                self._get_invitations_url(self.visible_project),
                {'users_to_invite': [invitee.username]})
            self.assertEqual(400, response.status_code)

            self.assertEqual(0, invitor.group_invitations_sent.count())
            self.assertEqual(0, invitee.group_invitations_received.count())

    def test_error_group_too_small(self):
        self.visible_project.allow_submissions_from_non_enrolled_students = True
        self.visible_project.min_group_size = 3
        self.visible_project.max_group_size = 3
        self.visible_project.validate_and_save()

        iterable = zip(
            (self.admin, self.staff, self.staff, self.enrolled, self.nobody),
            (self.admin_invitee, self.staff_invitee, self.admin_invitee,
             self.enrolled_invitee, self.nobody_invitee)
        )
        for invitor, invitee in iterable:
            client = MockClient(invitor)
            response = client.post(
                self._get_invitations_url(self.visible_project),
                {'users_to_invite': [invitee.username]})
            self.assertEqual(400, response.status_code)

            self.assertEqual(0, invitor.group_invitations_sent.count())
            self.assertEqual(0, invitee.group_invitations_received.count())
