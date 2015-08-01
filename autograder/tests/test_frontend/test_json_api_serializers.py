import json

from django.utils import timezone
from django.core.urlresolvers import reverse
from django.core.files.uploadedfile import SimpleUploadedFile

from autograder.tests.temporary_filesystem_test_case import (
    TemporaryFilesystemTestCase)

import autograder.tests.dummy_object_utils as obj_ut

from autograder.models import (
    Course, Semester, Project, AutograderTestCaseBase,
    Submission, SubmissionGroup)

from autograder.frontend.json_api_serializers import (
    course_to_json, semester_to_json, project_to_json)


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
                        'file_url': reverse('get-project-file',
                                            args=[self.project.pk, filename])
                    }
                    for filename in self.project.get_project_file_basenames()
                ],
                'visible_to_students': self.project.visible_to_students,
                'closing_time': self.project.closing_time,
                'disallow_student_submissions': self.project.disallow_student_submissions,
                'min_group_size': self.project.min_group_size,
                'max_group_size': self.project.max_group_size,
                'required_student_files': self.project.required_student_files,
                'expected_student_file_patterns': self.project.expected_student_file_patterns,
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
