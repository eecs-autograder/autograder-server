# TODO: Decide whether to keep this view

# from urllib.parse import urlencode

# from django.core.urlresolvers import reverse

# import autograder.utils.testing.model_obj_builders as obj_build
# from autograder.utils.testing import UnitTestBase
# import autograder.rest_api.tests.test_views.common_generic_data as test_data
# import autograder.rest_api.tests.test_views.common_test_impls as test_impls


# def result_url(result, student_view=None):
#     url = reverse('ag-test-result-detail', kwargs={'pk': result.pk})
#     if student_view is not None:
#         url += '?' + urlencode({'student_view': student_view})
#     return url


# class RetrieveResultTestCase(test_data.Client,
#                              test_data.Project,
#                              test_data.Submission,
#                              test_impls.GetObjectTest,
#                              UnitTestBase):
#     def test_staff_view_own_result(self):
#         for project in self.all_projects:
#             for group in self.staff_groups(project):
#                 submission = self.non_ultimate_submission(group)
#                 result = self.make_result(submission)
#                 self.do_get_object_test(
#                     self.client, group.members.first(), result_url(result),
#                     result.get_feedback(group.members.first()).to_dict())

#                 self.do_get_object_test(
#                     self.client, group.members.first(),
#                     result_url(result, student_view=True),
#                     result.get_feedback(group.members.first(),
#                                         student_view=True).to_dict())

#     def test_enrolled_view_own_result(self):
#         for project in self.visible_projects:
#             group = self.enrolled_group(project)
#             submission = self.non_ultimate_submission(group)
#             result = self.make_result(submission)
#             self.do_get_object_test(
#                 self.client, group.members.first(), result_url(result),
#                 result.get_feedback(group.members.first()).to_dict())

#     def test_non_enrolled_view_own_result(self):
#         group = self.non_enrolled_group(self.visible_public_project)
#         submission = self.non_ultimate_submission(group)
#         result = self.make_result(submission)
#         self.do_get_object_test(
#             self.client, group.members.first(), result_url(result),
#             result.get_feedback(group.members.first()).to_dict())

#     def test_staff_view_hidden_result_student_view_permission_denied(self):
#         project_settings = self.project.to_dict()
#         project_settings.pop('pk')
#         project_settings.pop('course')
#         for group in self.staff_groups(self.project):
#             for submission_func, key in (
#                     self.submission_funcs_and_ag_test_kwargs()):
#                 submission = submission_func(group)
#                 result = obj_build.build_compiled_ag_test_result(
#                     submission=submission,
#                     ag_test_kwargs={key: False})
#                 self.do_permission_denied_get_test(
#                     self.client, group.members.first(),
#                     result_url(result, student_view=True))

#                 self.project.validate_and_update(**project_settings)

#     def test_student_view_hidden_result_permission_denied(self):
#         project_settings = self.project.to_dict()
#         project_settings.pop('pk')
#         project_settings.pop('course')
#         for group in self.non_staff_groups(self.visible_public_project):
#             for submission_func, key in (
#                     self.submission_funcs_and_ag_test_kwargs()):
#                 submission = submission_func(group)
#                 result = obj_build.build_compiled_ag_test_result(
#                     submission=submission,
#                     ag_test_kwargs={key: False})
#                 self.do_permission_denied_get_test(
#                     self.client, group.members.first(), result_url(result))

#                 self.project.validate_and_update(**project_settings)

#     def test_staff_view_other_always_allowed(self):
#         project_settings = self.project.to_dict()
#         project_settings.pop('pk')
#         project_settings.pop('course')
#         for group in self.non_staff_groups(self.visible_public_project):
#             for submission_func, key in (
#                     self.submission_funcs_and_ag_test_kwargs()):
#                 submission = submission_func(group)
#                 result = obj_build.build_compiled_ag_test_result(
#                     submission=submission,
#                     ag_test_kwargs={key: False})
#                 for user in self.admin, self.staff:
#                     self.do_get_object_test(
#                         self.client, user,
#                         result_url(result, student_view=True),
#                         result.get_feedback(user, student_view=True).to_dict())

#                 self.project.validate_and_update(**project_settings)

#     def test_non_member_view_other_result_permission_denied(self):
#         other_user = self.clone_user(self.enrolled)
#         group = self.enrolled_group(self.visible_public_project)
#         for user in other_user, self.nobody:
#             submission = self.non_ultimate_submission(group)
#             result = self.make_result(submission)
#             self.do_permission_denied_get_test(
#                 self.client, user, result_url(result))

#     def test_enrolled_view_own_result_project_hidden_permission_denied(self):
#         for project in self.hidden_projects:
#             group = self.enrolled_group(project)
#             submission = self.non_ultimate_submission(group)
#             result = self.make_result(submission)
#             self.do_permission_denied_get_test(
#                 self.client, group.members.first(), result_url(result))

#     def test_non_enrolled_view_own_result_project_hidden_permission_denied(self):
#         group = self.non_enrolled_group(self.hidden_public_project)
#         submission = self.non_ultimate_submission(group)
#         result = self.make_result(submission)
#         self.do_permission_denied_get_test(
#             self.client, group.members.first(), result_url(result))

#     def test_non_enrolled_view_own_result_private_project_permission_denied(self):
#         group = self.non_enrolled_group(self.visible_public_project)
#         self.visible_public_project.validate_and_update(
#             allow_submissions_from_non_enrolled_students=False)
#         submission = self.non_ultimate_submission(group)
#         result = self.make_result(submission)
#         self.do_permission_denied_get_test(
#             self.client, group.members.first(), result_url(result))

#     def submission_funcs_and_ag_test_kwargs(self):
#         return [
#             [self.non_ultimate_submission, 'visible_to_students'],
#             [self.past_limit_submission, 'visible_in_past_limit_submission'],
#             [self.most_recent_ultimate_submission,
#              'visible_in_ultimate_submission'],
#         ]

#     def make_result(self, submission):
#         return obj_build.build_compiled_ag_test_result(
#             submission=submission,
#             ag_test_kwargs=self.all_visible_ag_test_kwargs())

#     def all_visible_ag_test_kwargs(self):
#         return {
#             'visible_to_students': True,
#             'visible_in_ultimate_submission': True,
#             'visible_in_past_limit_submission': True,
#         }
