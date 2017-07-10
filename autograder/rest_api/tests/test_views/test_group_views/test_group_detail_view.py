from django.core.urlresolvers import reverse
from django.utils import timezone

import autograder.core.models as ag_models

import autograder.utils.testing.model_obj_builders as obj_build
from autograder.utils.testing import UnitTestBase
import autograder.rest_api.tests.test_views.common_generic_data as test_data
import autograder.rest_api.tests.test_views.common_test_impls as test_impls


class RetrieveGroupTestCase(test_data.Client,
                            test_data.Project,
                            test_data.Group,
                            test_impls.GetObjectTest,
                            UnitTestBase):
    def test_admin_or_staff_get_group(self):
        for project in self.all_projects:
            for group in self.at_least_enrolled_groups(project):
                for user in self.admin, self.staff:
                    self.do_get_object_test(
                        self.client, user, self.group_url(group),
                        group.to_dict())

        for project in self.public_projects:
            group = self.non_enrolled_group(project)
            for user in self.admin, self.staff:
                self.do_get_object_test(
                    self.client, user, self.group_url(group), group.to_dict())

    def test_enrolled_get_group(self):
        for project in self.visible_projects:
            group = self.enrolled_group(project)
            for user in group.members.all():
                self.do_get_object_test(
                    self.client, user, self.group_url(group), group.to_dict())

    def test_non_enrolled_get_group(self):
        group = self.non_enrolled_group(self.visible_public_project)
        for user in group.members.all():
            self.do_get_object_test(
                self.client, user, self.group_url(group), group.to_dict())

    def test_non_member_view_group_permission_denied(self):
        group = self.enrolled_group(self.visible_public_project)
        non_member = self.clone_user(self.enrolled)
        for user in non_member, self.nobody:
            self.do_permission_denied_get_test(
                self.client, user, self.group_url(group))

    def test_enrolled_view_group_project_hidden_permission_denied(self):
        for project in self.hidden_projects:
            group = self.enrolled_group(project)
            self.do_permission_denied_get_test(
                self.client, self.enrolled, self.group_url(group))

    def test_non_enrolled_view_group_project_hidden_permission_denied(self):
        group = self.non_enrolled_group(self.hidden_public_project)
        self.do_permission_denied_get_test(
            self.client, self.nobody, self.group_url(group))

    def test_non_enrolled_view_group_project_private_permission_denied(self):
        group = self.non_enrolled_group(self.visible_public_project)
        self.visible_public_project.validate_and_update(
            guests_can_submit=False)
        self.do_permission_denied_get_test(
            self.client, self.nobody, self.group_url(group))


class UpdateGroupTestCase(test_data.Client,
                          test_data.Project,
                          test_data.Group,
                          test_impls.UpdateObjectTest,
                          UnitTestBase):
    def setUp(self):
        super().setUp()
        self.new_due_date = timezone.now().replace(microsecond=0)

    def get_names(self, users):
        return [user.username for user in users]

    def test_admin_update_admin_and_staff_group_members(self):
        for project in self.all_projects:
            group = self.staff_group(project)
            new_members = (list(group.members.all())[:-1] +
                           [self.clone_user(self.admin)])
            self.do_patch_object_test(
                group, self.client, self.admin, self.group_url(group),
                {'member_names': self.get_names(new_members)})

    def test_admin_update_enrolled_group_members(self):
        for project in self.all_projects:
            group = self.enrolled_group(project)
            new_members = (list(group.members.all())[:-1] +
                           [self.clone_user(self.enrolled)])
            self.do_patch_object_test(
                group, self.client, self.admin, self.group_url(group),
                {'member_names': self.get_names(new_members)})

    def test_admin_update_non_enrolled_group_members(self):
        for project in self.public_projects:
            group = self.non_enrolled_group(project)
            new_members = self.get_names(
                list(group.members.all())[:-1]) + ['stove']
            self.do_patch_object_test(
                group, self.client, self.admin, self.group_url(group),
                {'member_names': new_members})

    def test_admin_update_group_override_size(self):
        for project in self.all_projects:
            group = self.enrolled_group(project)
            new_members = (list(group.members.all()) +
                           [self.clone_user(self.enrolled)])
            self.assertGreater(len(new_members), project.max_group_size)
            self.do_patch_object_test(
                group, self.client, self.admin, self.group_url(group),
                {'member_names': self.get_names(new_members)})

    def test_admin_update_group_extension(self):
        for project in self.all_projects:
            group = self.enrolled_group(project)
            # give and revoke extension
            self.do_patch_object_test(
                group, self.client, self.admin, self.group_url(group),
                {'extended_due_date': self.new_due_date})
            self.do_patch_object_test(
                group, self.client, self.admin, self.group_url(group),
                {'extended_due_date': None})

        for project in self.public_projects:
            group = self.non_enrolled_group(project)
            self.do_patch_object_test(
                group, self.client, self.admin, self.group_url(group),
                {'extended_due_date': self.new_due_date})
            self.do_patch_object_test(
                group, self.client, self.admin, self.group_url(group),
                {'extended_due_date': None})

    def test_admin_update_group_invalid_members(self):
        for project in self.all_projects:
            group = self.enrolled_group(project)
            new_members = self.get_names(
                list(group.members.all())[:-1]) + ['stove']
            response = self.do_patch_object_invalid_args_test(
                group, self.client, self.admin, self.group_url(group),
                {'member_names': new_members})
            self.assertIn('members', response.data)

    def test_admin_update_group_bad_date(self):
        group = self.enrolled_group(self.visible_public_project)
        response = self.do_patch_object_invalid_args_test(
            group, self.client, self.admin, self.group_url(group),
            {'extended_due_date': 'not a date'})
        self.assertIn('extended_due_date', response.data)

    def test_other_update_group_permission_denied(self):
        for group in (self.staff_group(self.visible_public_project),
                      self.enrolled_group(self.visible_public_project),
                      self.non_enrolled_group(self.visible_public_project)):
            for user in self.staff, self.enrolled, self.nobody:
                self.do_patch_object_permission_denied_test(
                    group, self.client, user, self.group_url(group),
                    {'extended_due_date': self.new_due_date})

    # def test_update_group_new_members_pending_invitations_deleted(self):
    #     self.fail()


class RetrieveUltimateSubmissionTestCase(test_data.Client,
                                         test_data.Project,
                                         test_data.Group,
                                         test_impls.GetObjectTest,
                                         UnitTestBase):

    # IMPORTANT: hide_ultimate_submission_fdbk is True by default, so
    # make sure that you set it to False when you want to check other
    # permissions situations.

    def setUp(self):
        super().setUp()
        self.past_closing_time = timezone.now() - timezone.timedelta(minutes=5)
        self.not_past_extension = timezone.now() + timezone.timedelta(minutes=5)
        self.past_extension = timezone.now() - timezone.timedelta(minutes=1)

    def test_admin_or_staff_get_ultimate_submission(self):
        for closing_time in None, self.past_closing_time:
            self.do_get_ultimate_submission_test(
                self.all_projects,
                [self.admin_group, self.staff_group, self.enrolled_group],
                [self.admin, self.staff],
                closing_time=closing_time)

            self.do_get_ultimate_submission_test(
                [self.visible_public_project, self.hidden_public_project],
                [self.non_enrolled_group], [self.admin, self.staff],
                closing_time=closing_time)

    def test_admin_or_staff_get_own_ultimate_where_student_cant(self):
        # Admins and staff can always view their own ultimate submission.
        future_closing_time = timezone.now() + timezone.timedelta(minutes=4)
        self.do_get_ultimate_submission_test(
            [self.hidden_private_project], [self.admin_group], [self.admin],
            closing_time=future_closing_time, hide_ultimates=True)

        self.do_get_ultimate_submission_test(
            [self.hidden_private_project], [self.staff_group], [self.staff],
            closing_time=future_closing_time, hide_ultimates=True)

    def test_enrolled_get_ultimate_submission(self):
        for closing_time in None, self.past_closing_time:
            self.do_get_ultimate_submission_test(
                self.visible_projects, [self.enrolled_group], [self.enrolled],
                closing_time=closing_time)

    def test_non_enrolled_get_ultimate_submission(self):
        for closing_time in None, self.past_closing_time:
            self.do_get_ultimate_submission_test(
                [self.visible_public_project], [self.non_enrolled_group],
                [self.nobody], closing_time=closing_time)

    def test_non_member_get_ultimate_permission_denied(self):
        self.visible_public_project.validate_and_update(
            closing_time=self.past_closing_time,
            hide_ultimate_submission_fdbk=False)
        group = self.enrolled_group(self.visible_public_project)
        obj_build.build_finished_submission(submission_group=group)
        other_user = self.clone_user(self.enrolled)
        for user in self.nobody, other_user:
            self.do_permission_denied_get_test(
                self.client, user, self.ultimate_submission_url(group))

    def test_enrolled_get_ultimate_project_hidden_permission_denied(self):
        for project in self.hidden_projects:
            project.validate_and_update(
                closing_time=self.past_closing_time,
                hide_ultimate_submission_fdbk=False)
            group = self.enrolled_group(project)
            obj_build.build_finished_submission(submission_group=group)
            self.do_permission_denied_get_test(
                self.client, self.enrolled,
                self.ultimate_submission_url(group))

    def test_non_enrolled_get_ultimate_project_hidden_permission_denied(self):
        self.hidden_public_project.validate_and_update(
            closing_time=None, hide_ultimate_submission_fdbk=False)
        group = self.non_enrolled_group(self.hidden_public_project)
        obj_build.build_finished_submission(submission_group=group)
        self.do_permission_denied_get_test(
            self.client, self.nobody, self.ultimate_submission_url(group))

    def test_non_enrolled_get_ultimate_project_private_permission_denied(self):
        group = self.non_enrolled_group(self.visible_public_project)
        self.visible_public_project.validate_and_update(
            guests_can_submit=False,
            closing_time=self.past_closing_time,
            hide_ultimate_submission_fdbk=False)
        obj_build.build_finished_submission(submission_group=group)
        self.do_permission_denied_get_test(
            self.client, self.nobody, self.ultimate_submission_url(group))

    def test_deadline_not_past_student_view_own_ultimate_permission_denied(self):
        self.visible_public_project.validate_and_update(
            closing_time=timezone.now() + timezone.timedelta(minutes=5),
            hide_ultimate_submission_fdbk=False)
        for group in self.non_staff_groups(self.visible_public_project):
            obj_build.build_finished_submission(submission_group=group)
            self.do_permission_denied_get_test(
                self.client, group.members.first(),
                self.ultimate_submission_url(group))

    def test_deadline_not_past_admin_or_staff_view_other_ultimate_permission_denied(self):
        self.visible_public_project.validate_and_update(
            closing_time=timezone.now() + timezone.timedelta(minutes=5),
            hide_ultimate_submission_fdbk=False)
        for group in self.all_groups(self.visible_public_project):
            for user in self.admin, self.staff:
                if group.members.filter(pk=user.pk).exists():
                    continue
                self.do_permission_denied_get_test(
                    self.client, user, self.ultimate_submission_url(group))

    def test_deadline_past_or_none_but_ultimate_fdbk_hidden_permission_denied(self):
        for closing_time in None, self.past_closing_time:
            self.visible_public_project.validate_and_update(
                hide_ultimate_submission_fdbk=True,
                closing_time=closing_time)
            for group in self.non_staff_groups(self.visible_public_project):
                obj_build.build_finished_submission(submission_group=group)
                self.do_permission_denied_get_test(
                    self.client, group.members.first(),
                    self.ultimate_submission_url(group))

    def test_deadline_past_or_none_ultimate_fdbk_hidden_staff_can_view_all_others_ultimate(self):
        for closing_time in None, self.past_closing_time:
            self.do_get_ultimate_submission_test(
                [self.visible_public_project],
                [self.admin_group, self.staff_group,
                 self.enrolled_group, self.non_enrolled_group],
                [self.admin, self.staff], closing_time=closing_time,
                hide_ultimates=True)

    def test_extension_not_past_student_view_own_ultimate_permission_denied(self):
        self.visible_public_project.validate_and_update(
            closing_time=self.past_closing_time,
            hide_ultimate_submission_fdbk=False)
        for group in self.non_staff_groups(self.visible_public_project):
            group.validate_and_update(extended_due_date=self.not_past_extension)
            obj_build.build_finished_submission(submission_group=group)
            self.do_permission_denied_get_test(
                self.client, group.members.first(),
                self.ultimate_submission_url(group))

    def test_extension_not_past_admin_or_staff_view_other_ultimate_permission_denied(self):
        self.visible_public_project.validate_and_update(
            closing_time=self.past_closing_time,
            hide_ultimate_submission_fdbk=False)
        for group in self.all_groups(self.visible_public_project):
            group.validate_and_update(extended_due_date=self.not_past_extension)
            for user in self.admin, self.staff:
                if group.members.filter(pk=user.pk).exists():
                    continue
                self.do_permission_denied_get_test(
                    self.client, user, self.ultimate_submission_url(group))

    def test_extension_past_but_ultimate_fdbk_hidden_permission_denied(self):
        self.visible_public_project.validate_and_update(
            closing_time=self.past_closing_time,
            hide_ultimate_submission_fdbk=True)
        for group in self.non_staff_groups(self.visible_public_project):
            group.validate_and_update(extended_due_date=self.past_extension)
            obj_build.build_finished_submission(submission_group=group)
            self.do_permission_denied_get_test(
                self.client, group.members.first(),
                self.ultimate_submission_url(group))

    def test_extension_past_ultimate_fdbk_hidden_staff_can_view_all_others_ultimate(self):
        self.do_get_ultimate_submission_test(
            [self.visible_public_project],
            [self.admin_group, self.staff_group,
             self.enrolled_group, self.non_enrolled_group],
            [self.admin, self.staff],
            closing_time=self.past_closing_time,
            extension=self.past_extension,
            hide_ultimates=True)

    def do_get_ultimate_submission_test(self, projects, group_funcs, users,
                                        closing_time, extension=None,
                                        hide_ultimates=False):
        for project in projects:
            project.validate_and_update(
                closing_time=closing_time,
                hide_ultimate_submission_fdbk=hide_ultimates)
            for group_func in group_funcs:
                group = group_func(project)
                group.validate_and_update(extended_due_date=extension)

                suite = obj_build.make_ag_test_suite(project)
                case = obj_build.make_ag_test_case(suite)
                cmd = obj_build.make_full_ag_test_command(case)
                best_submission = obj_build.build_finished_submission(submission_group=group)
                most_recent_submission = obj_build.build_finished_submission(
                    submission_group=group)

                obj_build.make_correct_ag_test_command_result(cmd, submission=best_submission)
                obj_build.make_incorrect_ag_test_command_result(
                    cmd, submission=most_recent_submission)

                for user in users:
                    url = self.ultimate_submission_url(group)
                    project.validate_and_update(
                        ultimate_submission_policy=ag_models.UltimateSubmissionPolicy.most_recent)
                    self.do_get_object_test(
                        self.client, user, url, most_recent_submission.to_dict())

                    project.validate_and_update(
                        ultimate_submission_policy=ag_models.UltimateSubmissionPolicy.best)
                    self.do_get_object_test(self.client, user, url, best_submission.to_dict())

    def ultimate_submission_url(self, group):
        return reverse('group-ultimate-submission', kwargs={'pk': group.pk})
