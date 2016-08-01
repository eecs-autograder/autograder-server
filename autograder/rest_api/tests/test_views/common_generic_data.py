'''
The classes defined here serve as mixins for adding members to a class
that yield data commonly used in the REST API view test cases. Note that
database objects are not created until the first time they are accessed
per test case.
'''

from django.core.urlresolvers import reverse

from rest_framework.test import APIClient

import autograder.utils.testing.generic_data as gen_data


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

    def submissions_url(self, group):
        return reverse('group-submissions-list', kwargs={'group_pk': group.pk})


class Submission(gen_data.Submission):
    pass
