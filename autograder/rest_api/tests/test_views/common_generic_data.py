'''
The classes defined here serve as mixins for adding members to a class
that yield data commonly used in the REST API view test cases. Note that
database objects are not created until the first time they are accessed
per test case.
'''

import random
import copy

from django.core.urlresolvers import reverse

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
    def get_proj_url(self, project):
        return reverse('project-detail', kwargs={'pk': project.pk})

    def get_patterns_url(self, project):
        return reverse('project-expected-patterns-list',
                       kwargs={'project_pk': project.pk})

    def get_uploaded_files_url(self, project):
        return reverse('project-uploaded-files-list',
                       kwargs={'project_pk': project.pk})

    def get_groups_url(self, project):
        return reverse('project-groups-list',
                       kwargs={'project_pk': project.pk})

    def get_invitations_url(self, project):
        return reverse('project-group-invitations-list',
                       kwargs={'project_pk': project.pk})

    def get_ag_tests_url(self, project):
        return reverse('project-ag-tests-list',
                       kwargs={'project_pk': project.pk})

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
    def projects_hidden_from_non_enrolled(self):
        return [self.visible_private_project] + self.hidden_projects

    @property
    def all_projects(self):
        return self.visible_projects + self.hidden_projects


class Group(Course):
    def setUp(self):
        super().setUp()
        # For caching
        self._invitations = {
            # <project pk>: {
            #   <label>: <invitation object>
            # }
        }

    def invitation_url(self, invitation):
        return reverse('group-invitation-detail', kwargs={'pk': invitation.pk})

    def admin_group_invitation(self, project):
        label = '_admin_group_invitation'
        return self._build_invitation(project, self.admin, label)

    def staff_group_invitation(self, project):
        label = '_staff_group_invitation'
        return self._build_invitation(project, self.staff, label)

    def enrolled_group_invitation(self, project):
        label = '_enrolled_group_invitation'
        return self._build_invitation(project, self.enrolled, label)

    def non_enrolled_group_invitation(self, project):
        label = '_non_enrolled_group_invitation'
        return self._build_invitation(project, self.nobody, label)

    def _build_invitation(self, project, user_to_clone, label):
        if project.max_group_size < 3:
            project.validate_and_update(max_group_size=3)

        invitation = self._get_cached(project, label)
        if invitation is not None:
            return invitation

        invitees = [self.clone_user(user_to_clone) for i in range(2)]
        invitation = ag_models.SubmissionGroupInvitation.objects.validate_and_create(
            user_to_clone, invitees, project=project)

        self._store(project, label, invitation)
        return invitation

    def _build_group(self, project, user_to_clone):
        if project.max_group_size < 3:
            project.validate_and_update(max_group_size=3)

        members = ([user_to_clone] +
                   [self.clone_user(user_to_clone) for i in range(2)])
        return ag_models.SubmissionGroup.objects.validate_and_create(
            members, project=project)

    # -------------------------------------------------------------------------

    def clone_user(self, user):
        new_user = copy.copy(user)
        new_user.pk = None
        new_user.username = obj_ut.get_unique_id()
        new_user.save()
        new_user.courses_is_admin_for.add(*user.courses_is_admin_for.all())
        new_user.courses_is_staff_for.add(*user.courses_is_staff_for.all())
        new_user.courses_is_enrolled_in.add(*user.courses_is_enrolled_in.all())

        return new_user

    def _get_cached(self, project, label):
        try:
            return self._invitations[project.pk][label]
        except KeyError:
            return None

    def _store(self, project, label, invitation):
        if project.pk not in self._invitations:
            self._invitations[project.pk] = {}
            self._invitations[project.pk][label] = invitation
