'''
The classes defined here serve as mixins for building a singleton with
data commonly used in the REST API view test cases.
Note that a given database object is not created until the first time it is
accessed per test case.
'''

import random

from rest_framework.test import APIClient

import autograder.core.models as ag_models

import autograder.core.tests.dummy_object_utils as obj_ut


class Client:
    def setUp(self):
        super().setUp()
        self.client = APIClient()


class Superuser:
    @property
    def superuser(self):
        if not hasattr(self, '_superuser'):
            self._superuser = obj_ut.create_dummy_user(is_superuser=True)

        return self._superuser


class Course:
    @property
    def course(self):
        if not hasattr(self, '_course'):
            self._course = obj_ut.build_course()

        return self._course

    @property
    def admin(self):
        if not hasattr(self, '_admin'):
            self._admin = obj_ut.create_dummy_user()
            self.course.administrators.add(self._admin)

        return self._admin

    @property
    def staff(self):
        if not hasattr(self, '_staff'):
            self._staff = obj_ut.create_dummy_user()
            self.course.staff.add(self._staff)

        return self._staff

    @property
    def enrolled(self):
        if not hasattr(self, '_enrolled'):
            self._enrolled = obj_ut.create_dummy_user()
            self.course.enrolled_students.add(self._enrolled)

        return self._enrolled

    @property
    def nobody(self):
        if not hasattr(self, '_nobody'):
            self._nobody = obj_ut.create_dummy_user()

        return self._nobody


class Project(Course):
    @property
    def project(self):
        if not hasattr(self, '_project'):
            self._project = ag_models.Project.objects.validate_and_create(
                name='spammy' + random.choice('qewiurqelrhjk'),
                course=self.course)

        return self._project

    @property
    def visible_public_project(self):
        if not hasattr(self, '_visible_public_project'):
            self._visible_public_project = (
                ag_models.Project.objects.validate_and_create(
                    name='visible_public_project',
                    course=self.course,
                    visible_to_students=True,
                    allow_submissions_from_non_enrolled_students=True))

        return self._visible_public_project

    @property
    def visible_private_project(self):
        if not hasattr(self, '_visible_private_project'):
            self._visible_private_project = (
                ag_models.Project.objects.validate_and_create(
                    name='visible_private_project',
                    course=self.course,
                    visible_to_students=True,
                    allow_submissions_from_non_enrolled_students=False))

        return self._visible_private_project

    @property
    def hidden_public_project(self):
        if not hasattr(self, '_hidden_public_project'):
            self._hidden_public_project = (
                ag_models.Project.objects.validate_and_create(
                    name='hidden_public_project',
                    course=self.course,
                    visible_to_students=False,
                    allow_submissions_from_non_enrolled_students=True))

        return self._hidden_public_project

    @property
    def hidden_private_project(self):
        if not hasattr(self, '_hidden_private_project'):
            self._hidden_private_project = (
                ag_models.Project.objects.validate_and_create(
                    name='hidden_private_project',
                    course=self.course,
                    visible_to_students=False,
                    allow_submissions_from_non_enrolled_students=False))

        return self._hidden_private_project

    @property
    def visible_projects(self):
        return [self.visible_public_project, self.visible_private_project]

    @property
    def hidden_projects(self):
        return [self.hidden_public_project, self.hidden_private_project]

    @property
    def all_projects(self):
        return self.visible_projects + self.hidden_projects
