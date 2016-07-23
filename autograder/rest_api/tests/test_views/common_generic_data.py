'''
The classes defined here serve as mixins for adding members to a class
that yield data commonly used in the REST API view test cases. Note that
database objects are not created until the first time they are accessed
per test case.
'''

from django.core.urlresolvers import reverse

from rest_framework.test import APIClient

import autograder.core.tests.generic_data as gen_data


class Client:
    def setUp(self):
        super().setUp()
        self.client = APIClient()


class Superuser(gen_data.Superuser):
    pass


class Course(gen_data.Course):
    pass


class Project(gen_data.Project):
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


class Group(gen_data.Group):
    def invitation_url(self, invitation):
        return reverse('group-invitation-detail', kwargs={'pk': invitation.pk})

    def group_url(self, group):
        return reverse('group-detail', kwargs={'pk': group.pk})


class Submission(gen_data.Submission):
    pass

# class AGTestResult(Submission):
#     def setUp(self):
#         super().setUp()
#         self._submissions = {
#             # <group pk>: {
#             #   <label>: <submission>
#             # }
#         }

#     def admin_result(self, project, **ag_test_kwargs):
#         results, ag_tests, submission = self.admin_results(
#             project, **ag_test_kwargs)
#         return results[0], ag_tests[0], submission

#     def staff_result(self, project, **ag_test_kwargs):
#         results, ag_tests, submission = self.staff_results(
#             project, **ag_test_kwargs)
#         return results[0], ag_tests[0], submission

#     def enrolled_result(self, project, **ag_test_kwargs):
#         results, ag_tests, submission = self.enrolled_results(
#             project, **ag_test_kwargs)
#         return results[0], ag_tests[0], submission

#     def non_enrolled_result(self, project, **ag_test_kwargs):
#         results, ag_tests, submission = self.non_enrolled_results(
#             project, **ag_test_kwargs)
#         return results[0], ag_tests[0], submission

#     def admin_results(self, project, num_results=1, **ag_test_kwargs):
#         submission = self._get_cached_submission(project, 'admin')
#         if submission is None:
#             submission = self.build_submission(self.admin_group(project))
#             self._store_submission(project, 'admin', submission)
#         return self._make_results(submission, num_results, **ag_test_kwargs)

#     def staff_results(self, project, num_results=1, **ag_test_kwargs):
#         submission = self._get_cached_submission(project, 'staff')
#         if submission is None:
#             submission = self.build_submission(self.staff_group(project))
#             self._store_submission(project, 'staff', submission)
#         return self._make_results(submission, num_results, **ag_test_kwargs)

#     def enrolled_results(self, project, num_results=1, **ag_test_kwargs):
#         submission = self._get_cached_submission(project, 'enrolled')
#         if submission is None:
#             submission = self.build_submission(self.enrolled_group(project))
#             self._store_submission(project, 'enrolled', submission)
#         return self._make_results(submission, num_results, **ag_test_kwargs)

#     def non_enrolled_results(self, project, num_results=1, **ag_test_kwargs):
#         submission = self._get_cached_submission(project, 'non_enrolled')
#         if submission is None:
#             submission = self.build_submission(self.non_enrolled_group(project))
#             self._store_submission(project, 'non_enrolled', submission)
#         return self._make_results(submission, num_results, **ag_test_kwargs)

#     def _make_results(self, submission, num_results, **ag_test_kwargs):
#         ag_tests = [obj_ut.build_compiled_ag_test(**ag_test_kwargs)
#                     for i in range(num_results)]
#         results = [
#             ag_models.AutograderTestCaseResult.objects.validate_and_create(
#                 test_case=ag_test, submission=submission)
#             for ag_test in ag_tests
#         ]

#         return results, ag_tests, submission

#     def _get_cached_submission(self, project, label):
#         try:
#             return self._submissions[project.pk][label]
#         except KeyError:
#             return None

#     def _store_submission(self, project, label, submission):
#         if project.pk not in self._submissions:
#             self._submissions[project.pk] = {}

#         self._submissions[project.pk][label] = submission
