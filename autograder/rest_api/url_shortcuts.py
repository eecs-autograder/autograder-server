from django.core.urlresolvers import reverse


def get_course(course):
    return reverse('course:get', kwargs={'pk': course.pk})


def get_course_admins(course):
    return reverse('course:admins', kwargs={'pk': course.pk})


def get_semesters(course):
    return reverse('course:semesters', kwargs={'pk': course.pk})


def get_semester(semester):
    return reverse('semester:get', kwargs={'pk': semester.pk})
