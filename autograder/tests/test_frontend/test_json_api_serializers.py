from django.utils import timezone
from django.core.urlresolvers import reverse
from django.core.files.uploadedfile import SimpleUploadedFile

from autograder.tests.temporary_filesystem_test_case import (
    TemporaryFilesystemTestCase)

import autograder.tests.dummy_object_utils as obj_ut

from autograder.frontend.json_api_serializers import (
    course_to_json, semester_to_json, project_to_json,
    autograder_test_case_to_json, submission_group_to_json)

from autograder.models import CompiledAutograderTestCase, SubmissionGroup

# print(json.dumps(expected, sort_keys=True, indent=4))
# print(json.dumps(actual, sort_keys=True, indent=4))


class CourseSerializerTestCase(TemporaryFilesystemTestCase):
    def setUp(self):
        super().setUp()

        self.course = obj_ut.create_dummy_courses()

    def test_serialize_course_with_fields(self):
        user = obj_ut.create_dummy_users()
        self.course.add_course_admins(user)

        expected = {
            'type': 'course',
            'id': self.course.pk,
            'attributes': {
                'name': self.course.name,
                'course_admin_names': [user.username]
            },
            'links': {
                'self': reverse('get-course', args=[self.course.pk])
            }
        }

        actual = course_to_json(self.course)

        self.assertEqual(expected, actual)

    def test_serialize_course_without_fields(self):
        expected = {
            'type': 'course',
            'id': self.course.pk,
            'links': {
                'self': reverse('get-course', args=[self.course.pk])
            }
        }

        actual = course_to_json(self.course, with_fields=False)

        self.assertEqual(expected, actual)


# -----------------------------------------------------------------------------
# -----------------------------------------------------------------------------

class SemesterSerializerTestCase(TemporaryFilesystemTestCase):
    def setUp(self):
        super().setUp()

        self.course = obj_ut.create_dummy_courses()
        self.semester = obj_ut.create_dummy_semesters(self.course)

        self.staff = obj_ut.create_dummy_users()
        self.semester.add_semester_staff(self.staff)

        self.admin = obj_ut.create_dummy_users()
        self.course.add_course_admins(self.admin)

        self.enrolled_student = obj_ut.create_dummy_users()
        self.semester.add_enrolled_students(self.enrolled_student)

    def test_serialize_semester_with_fields_is_staff(self):
        expected = {
            'type': 'semester',
            'id': self.semester.pk,
            'attributes': {
                'name': self.semester.name,
                'semester_staff_names': self.semester.semester_staff_names,
                'enrolled_student_names': self.semester.enrolled_student_names
            },
            'relationships': {
                'course': {
                    'data': {
                        'type': 'course',
                        'id': self.course.pk,
                        'links': {
                            'self': reverse(
                                'get-course', args=[self.course.pk]),
                        },
                    }
                }
            },
            'links': {
                'self': reverse('semester-handler', args=[self.semester.pk])
            },
            'meta': {
                'is_staff': True,
                'course_admin_names': self.course.course_admin_names
            }
        }

        actual = semester_to_json(self.semester, user_is_semester_staff=True)

        self.assertEqual(expected, actual)

    def test_serialize_semester_with_fields_not_staff(self):
        expected = {
            'type': 'semester',
            'id': self.semester.pk,
            'attributes': {
                'name': self.semester.name,
            },
            'relationships': {
                'course': {
                    'data': {
                        'type': 'course',
                        'id': self.course.pk,
                        'links': {
                            'self': reverse(
                                'get-course', args=[self.course.pk]),
                        },
                    }
                }
            },
            'links': {
                'self': reverse('semester-handler', args=[self.semester.pk])
            },
            'meta': {
                'is_staff': False
            }
        }

        actual = semester_to_json(self.semester, user_is_semester_staff=False)

        self.assertEqual(expected, actual)

    def test_serialize_semester_no_fields_is_staff(self):
        expected = {
            'type': 'semester',
            'id': self.semester.pk,
            'links': {
                'self': reverse('semester-handler', args=[self.semester.pk])
            },
            'meta': {
                'is_staff': True
            }
        }

        actual = semester_to_json(
            self.semester, with_fields=False, user_is_semester_staff=True)

        self.assertEqual(expected, actual)

    def test_serialize_semester_no_fields_not_staff(self):
        expected = {
            'type': 'semester',
            'id': self.semester.pk,
            'links': {
                'self': reverse('semester-handler', args=[self.semester.pk])
            },
            'meta': {
                'is_staff': False
            }
        }

        actual = semester_to_json(
            self.semester, with_fields=False, user_is_semester_staff=False)

        self.assertEqual(expected, actual)


# -----------------------------------------------------------------------------
# -----------------------------------------------------------------------------

class ProjectSerializerTestCase(TemporaryFilesystemTestCase):
    def setUp(self):
        super().setUp()

        self.course = obj_ut.create_dummy_courses()
        self.semester = obj_ut.create_dummy_semesters(self.course)

        self.project = obj_ut.create_dummy_projects(self.semester)

        self.project.closing_time = timezone.now()
        self.project.max_group_size = 5

        self.project.required_student_files = ['spam', 'egg']
        self.project.add_project_file(
            SimpleUploadedFile('cheese.txt', b'cheeeese'))

    def test_serialize_project_with_fields(self):
        expected = {
            'type': 'project',
            'id': self.project.pk,
            'links': {
                'self': reverse('project-handler', args=[self.project.pk])
            },
            'attributes': {
                'name': self.project.name,
                'project_files': [
                    {
                        'filename': filename,
                        'size': self.project.get_file(filename).size,
                        'file_url': reverse('project-file-handler',
                                            args=[self.project.pk, filename])
                    }
                    for filename in self.project.get_project_file_basenames()
                ],
                'test_case_feedback_configuration': (
                    self.project.test_case_feedback_configuration.to_json()),
                'visible_to_students': self.project.visible_to_students,
                'closing_time': self.project.closing_time,
                'disallow_student_submissions': (
                    self.project.disallow_student_submissions),
                'allow_submissions_from_non_enrolled_students': (
                    self.project.allow_submissions_from_non_enrolled_students),
                'min_group_size': self.project.min_group_size,
                'max_group_size': self.project.max_group_size,
                'required_student_files': self.project.required_student_files,
                'expected_student_file_patterns': (
                    self.project.expected_student_file_patterns),
            },
            'relationships': {
                'semester': {
                    'data': semester_to_json(self.semester, with_fields=False)
                }
            }
        }

        actual = project_to_json(self.project)

        self.assertEqual(expected, actual)

    def test_serialize_project_no_fields(self):
        expected = {
            'type': 'project',
            'id': self.project.pk,
            'links': {
                'self': reverse('project-handler', args=[self.project.pk])
            }
        }

        actual = project_to_json(self.project, with_fields=False)

        self.assertEqual(expected, actual)


# -----------------------------------------------------------------------------
# -----------------------------------------------------------------------------

class AutograderTestCaseSerializerTestCase(TemporaryFilesystemTestCase):
    def setUp(self):
        super().setUp()

        self.course = obj_ut.create_dummy_courses()
        self.semester = obj_ut.create_dummy_semesters(self.course)

        self.project = obj_ut.create_dummy_projects(self.semester)

        self.project.required_student_files = ['spam.cpp', 'egg.cpp']
        self.project.add_project_file(
            SimpleUploadedFile('cheese.txt', b'cheeeese'))

        self.ag_test = CompiledAutograderTestCase.objects.validate_and_create(
            name='test',
            project=self.project,
            hide_from_students=False,
            command_line_arguments=['argy', 'argy2'],
            standard_input='iiiin',
            test_resource_files=['cheese.txt'],
            time_limit=5,
            expected_return_code=0,
            expect_any_nonzero_return_code=False,
            expected_standard_output='stdouuuut',
            expected_standard_error_output='stderrrr',
            use_valgrind=True,
            valgrind_flags=['--leak-check=full', '--error-exitcode=42'],
            compiler='g++',
            compiler_flags=['-Wall'],
            files_to_compile_together=['spam.cpp', 'egg.cpp'],
            executable_name='prog',
            points_for_correct_return_code=42,
            points_for_correct_output=3,
            points_for_no_valgrind_errors=9001,
            points_for_compilation_success=75)

    def test_serialize_test_case_with_fields(self):
        expected = {
            'type': 'compiled_test_case',
            'id': self.ag_test.pk,
            'links': {
                'self': reverse('ag-test-handler', args=[self.ag_test.pk])
            },
            'attributes': {
                'name': 'test',
                'hide_from_students': False,
                'command_line_arguments': ['argy', 'argy2'],
                'standard_input': 'iiiin',
                'test_resource_files': ['cheese.txt'],
                'time_limit': 5,
                'expected_return_code': 0,
                'expect_any_nonzero_return_code': False,
                'expected_standard_output': 'stdouuuut',
                'expected_standard_error_output': 'stderrrr',
                'use_valgrind': True,
                'valgrind_flags': ['--leak-check=full', '--error-exitcode=42'],
                'compiler': 'g++',
                'compiler_flags': ['-Wall'],
                'files_to_compile_together': ['spam.cpp', 'egg.cpp'],
                'executable_name': 'prog',

                'points_for_correct_return_code': 42,
                'points_for_correct_output': 3,
                'points_for_no_valgrind_errors': 9001,
                'points_for_compilation_success': 75
            },
            'relationships': {
                'project': {
                    'data': project_to_json(self.project, with_fields=False)
                }
            }
        }

        actual = autograder_test_case_to_json(self.ag_test)

        self.assertEqual(expected, actual)

    def test_serialize_test_case_without_fields(self):
        expected = {
            'type': 'compiled_test_case',
            'id': self.ag_test.pk,
            'links': {
                'self': reverse('ag-test-handler', args=[self.ag_test.pk])
            }
        }

        actual = autograder_test_case_to_json(self.ag_test, with_fields=False)

        self.assertEqual(expected, actual)


# -----------------------------------------------------------------------------
# -----------------------------------------------------------------------------

class SubmissionGroupSerializerTestCase(TemporaryFilesystemTestCase):
    def setUp(self):
        super().setUp()

        self.course = obj_ut.create_dummy_courses()
        self.semester = obj_ut.create_dummy_semesters(self.course)

        self.project = obj_ut.create_dummy_projects(self.semester)
        self.project.max_group_size = 2
        self.project.save()

        self.members = obj_ut.create_dummy_users(2)
        self.semester.add_enrolled_students(*self.members)
        self.member_names = [user.username for user in self.members]
        self.due_date = timezone.now()
        self.submission_group = SubmissionGroup.objects.create_group(
            self.members, self.project, extended_due_date=self.due_date)

    def test_serialize_submission_group_with_fields(self):
        expected = {
            'type': 'submission_group',
            'id': self.submission_group.pk,
            'attributes': {
                'members': sorted(self.member_names),
                'extended_due_date': self.due_date
            },
            'relationships': {
                'project': {
                    'data': project_to_json(self.project, with_fields=False)
                }
            }
        }

        actual = submission_group_to_json(self.submission_group)
        actual['attributes']['members'].sort()

        self.assertEqual(expected, actual)

    def test_serialize_submission_group_without_fields(self):
        expected = {
            'type': 'submission_group',
            'id': self.submission_group.pk
        }

        actual = submission_group_to_json(
            self.submission_group, with_fields=False)

        self.assertEqual(expected, actual)
