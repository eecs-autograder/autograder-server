from django.core.urlresolvers import reverse


def get_course(course):
    return reverse('course:get', kwargs={'pk': course.pk})


def get_course_admins(course):
    return reverse('course:admins', kwargs={'pk': course.pk})


def get_semesters(course):
    return reverse('course:semesters', kwargs={'pk': course.pk})


def get_semester(semester):
    return reverse('semester:get', kwargs={'pk': semester.pk})


def get_semester_staff(semester):
    return reverse('semester:staff', kwargs={'pk': semester.pk})


def get_semester_enrolled(semester):
    return reverse('semester:enrolled_students', kwargs={'pk': semester.pk})


def get_projects(semester):
    return reverse('semester:projects', kwargs={'pk': semester.pk})


def get_project(project):
    return reverse('project:get', kwargs={'pk': project.pk})


def get_project_files(project):
    return reverse('project:files', kwargs={'pk': project.pk})
