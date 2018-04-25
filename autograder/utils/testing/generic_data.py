import copy
import warnings

from django.core.files.uploadedfile import SimpleUploadedFile

import autograder.core.models as ag_models
from autograder.utils.testing import model_obj_builders as obj_build

warnings.warn(
    "generic_data is deprecated. "
    "Use autograder.utils.testing.model_obj_builders and "
    "test fixtures (setUp) instead", DeprecationWarning,
    stacklevel=2)


class Superuser:
    @property
    def superuser(self):
        if not hasattr(self, '_superuser'):
            self._superuser = obj_build.create_dummy_user(is_superuser=True)

        return self._superuser


class Course:
    @property
    def course(self):
        if not hasattr(self, '_course'):
            self._course = obj_build.build_course()

        return self._course

    @property
    def admin(self):
        if not hasattr(self, '_admin'):
            self._admin = obj_build.create_dummy_user()
            self.course.admins.add(self._admin)

        return self._admin

    @property
    def staff(self):
        if not hasattr(self, '_staff'):
            self._staff = obj_build.create_dummy_user()
            self.course.staff.add(self._staff)

        return self._staff

    @property
    def enrolled(self):
        if not hasattr(self, '_enrolled'):
            self._enrolled = obj_build.create_dummy_user()
            self.course.students.add(self._enrolled)

        return self._enrolled

    @property
    def handgrader(self):
        if not hasattr(self, '_handgrader'):
            self._handgrader = obj_build.create_dummy_user()
            self.course.handgraders.add(self._handgrader)

        return self._handgrader

    @property
    def nobody(self):
        if not hasattr(self, '_nobody'):
            self._nobody = obj_build.create_dummy_user()

        return self._nobody


class Project(Course):
    @property
    def project(self):
        if not hasattr(self, '_project'):
            self._project = obj_build.build_project(project_kwargs={'course': self.course})

        return self._project

    @property
    def visible_public_project(self):
        if not hasattr(self, '_visible_public_project'):
            self._visible_public_project = (
                ag_models.Project.objects.validate_and_create(
                    name='visible_public_project',
                    course=self.course,
                    visible_to_students=True,
                    guests_can_submit=True))

        return self._visible_public_project

    @property
    def visible_private_project(self):
        if not hasattr(self, '_visible_private_project'):
            self._visible_private_project = (
                ag_models.Project.objects.validate_and_create(
                    name='visible_private_project',
                    course=self.course,
                    visible_to_students=True,
                    guests_can_submit=False))

        return self._visible_private_project

    @property
    def hidden_public_project(self):
        if not hasattr(self, '_hidden_public_project'):
            self._hidden_public_project = (
                ag_models.Project.objects.validate_and_create(
                    name='hidden_public_project',
                    course=self.course,
                    visible_to_students=False,
                    guests_can_submit=True))

        return self._hidden_public_project

    @property
    def hidden_private_project(self):
        if not hasattr(self, '_hidden_private_project'):
            self._hidden_private_project = (
                ag_models.Project.objects.validate_and_create(
                    name='hidden_private_project',
                    course=self.course,
                    visible_to_students=False,
                    guests_can_submit=False))

        return self._hidden_private_project

    @property
    def visible_projects(self):
        return [self.visible_public_project, self.visible_private_project]

    @property
    def hidden_projects(self):
        return [self.hidden_public_project, self.hidden_private_project]

    @property
    def public_projects(self):
        return [self.visible_public_project, self.hidden_public_project]

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

        self._groups = {
            # <project pk>: {
            #   <label>: <group object>
            # }
        }

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

        invitation = self._get_cached_invitation(project, label)
        if invitation is not None:
            return invitation

        invitees = [self.clone_user(user_to_clone) for i in range(2)]
        invitation = ag_models.SubmissionGroupInvitation.objects.validate_and_create(
            user_to_clone, invitees, project=project)

        self._store_invitation(project, label, invitation)
        return invitation

    # -------------------------------------------------------------------------

    def admin_group(self, project, group_size=3):
        return self._build_group(project, self.admin, 'admin_group',
                                 group_size=group_size)

    def staff_group(self, project, group_size=3):
        return self._build_group(project, self.staff, 'staff_group',
                                 group_size=group_size)

    def enrolled_group(self, project, group_size=3):
        return self._build_group(project, self.enrolled, 'enrolled_group',
                                 group_size=group_size)

    def non_enrolled_group(self, project, group_size=3):
        return self._build_group(project, self.nobody, 'non_enrolled_group',
                                 group_size=group_size)

    def all_groups(self, project, group_size=3):
        return [self.admin_group(project, group_size=group_size),
                self.staff_group(project, group_size=group_size),
                self.enrolled_group(project, group_size=group_size),
                self.non_enrolled_group(project, group_size=group_size)]

    def at_least_enrolled_groups(self, project, group_size=3):
        return [self.admin_group(project, group_size=group_size),
                self.staff_group(project, group_size=group_size),
                self.enrolled_group(project, group_size=group_size)]

    def non_staff_groups(self, project, group_size=3):
        return [self.enrolled_group(project, group_size=group_size),
                self.non_enrolled_group(project, group_size=group_size)]

    def staff_groups(self, project, group_size=3):
        return [self.admin_group(project, group_size=group_size),
                self.staff_group(project, group_size=group_size)]

    def _build_group(self, project, user_to_clone, label, group_size):
        if project.max_group_size < group_size:
            project.validate_and_update(max_group_size=group_size)

        group = self._get_cached_group(project, label)
        if group is not None:
            return group

        members = ([user_to_clone] +
                   [self.clone_user(user_to_clone) for i in range(2)])
        group = ag_models.SubmissionGroup.objects.validate_and_create(
            members, project=project)
        self._store_group(project, label, group)
        return group

    # -------------------------------------------------------------------------

    def clone_user(self, user):
        new_user = copy.copy(user)
        new_user.pk = None
        new_user.username = obj_build.get_unique_id()
        new_user.save()
        new_user.courses_is_admin_for.add(*user.courses_is_admin_for.all())
        new_user.courses_is_staff_for.add(*user.courses_is_staff_for.all())
        new_user.courses_is_enrolled_in.add(*user.courses_is_enrolled_in.all())

        return new_user

    def _get_cached_invitation(self, project, label):
        try:
            return self._invitations[project.pk][label]
        except KeyError:
            return None

    def _store_invitation(self, project, label, invitation):
        if project.pk not in self._invitations:
            self._invitations[project.pk] = {}
            self._invitations[project.pk][label] = invitation

    def _get_cached_group(self, project, label):
        try:
            return self._groups[project.pk][label]
        except KeyError:
            return None

    def _store_group(self, project, label, group):
        if project.pk not in self._groups:
            self._groups[project.pk] = {}

        self._groups[project.pk][label] = group


# Note that submissions are not cached. Many of these functions modify
# the project associated with the group they are given in order
# to satisfy requirements for the type of object being requested.
class Submission(Group):
    def admin_submission(self, project):
        return self.build_submission(self.admin_group(project))

    def staff_submission(self, project):
        return self.build_submission(self.staff_group(project))

    def enrolled_submission(self, project):
        return self.build_submission(self.enrolled_group(project))

    def non_enrolled_submission(self, project):
        return self.build_submission(self.non_enrolled_group(project))

    def all_submissions(self, project):
        return [self.build_submission(group)
                for group in self.all_groups(project)]

    def at_least_enrolled_submissions(self, project):
        return [self.build_submission(group)
                for group in self.at_least_enrolled_groups(project)]

    def non_staff_submissions(self, project):
        return [self.build_submission(group)
                for group in self.non_staff_groups(project)]

    def staff_submissions(self, project):
        return [self.build_submission(group)
                for group in self.staff_groups(project)]

    @property
    def files_to_submit(self):
        return [
            SimpleUploadedFile('spam.cpp', b'steve'),
            SimpleUploadedFile('egg.txt', b'stave'),
            SimpleUploadedFile('sausage.txt', b'stove')
        ]

    def add_expected_patterns(self, project):
        if project.expected_student_files.count():
            return

        ag_models.ExpectedStudentFile.objects.validate_and_create(
            pattern='spam.cpp', project=project)
        ag_models.ExpectedStudentFile.objects.validate_and_create(
            pattern='*.txt', project=project, max_num_matches=3)

    def build_submission(self, group):
        self.add_expected_patterns(group.project)

        return ag_models.Submission.objects.validate_and_create(
            self.files_to_submit, submission_group=group,
            submitter=group.members.first().username)

    def build_submissions(self, group):
        submissions = []
        for i in range(group.members.count()):
            submissions.append(self.build_submission(group))

        return submissions
