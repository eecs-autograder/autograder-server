import os
from django.core.urlresolvers import reverse


def course_url(course):
    return reverse('course:get', kwargs={'pk': course.pk})


def course_admins_url(course):
    return reverse('course:admins', kwargs={'pk': course.pk})


def semesters_url(course):
    return reverse('course:semesters', kwargs={'pk': course.pk})


def semester_url(semester):
    return reverse('semester:get', kwargs={'pk': semester.pk})


def semester_staff_url(semester):
    return reverse('semester:staff', kwargs={'pk': semester.pk})


def semester_enrolled_url(semester):
    return reverse('semester:enrolled_students', kwargs={'pk': semester.pk})


def projects_url(semester):
    return reverse('semester:projects', kwargs={'pk': semester.pk})


def project_url(project):
    return reverse('project:get', kwargs={'pk': project.pk})


def project_files_url(project):
    return reverse('project:files', kwargs={'pk': project.pk})


def project_file_url(project, filename):
    return reverse(
        'project:file',
        kwargs={'pk': project.pk, 'filename': os.path.basename(filename)})


def ag_test_url(ag_test):
    return reverse('ag-test:get', kwargs={'pk': ag_test.pk})


def suite_url(suite):
    return reverse('suite:get', kwargs={'pk': suite.pk})


def group_url(group):
    return reverse('group:get', kwargs={'pk': group.pk})


def invitation_url(invitation):
    return reverse('invitation:get', kwargs={'pk': invitation.pk})


def submissions_url(group):
    return reverse('group:submissions', kwargs={'pk': group.pk})
