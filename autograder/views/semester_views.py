from django.views.generic.base import View
from django.views.generic.edit import CreateView, DeleteView

from django.core.exceptions import ValidationError
from django.forms.forms import NON_FIELD_ERRORS

from django.shortcuts import get_object_or_404, render

from django.core.urlresolvers import reverse_lazy
from django.http import HttpResponseRedirect

from autograder.models import Course, Semester


class ShowCourseList(CreateView):
    template_name = 'autograder/course_list.html'
    model = Course
    fields = ['name']
    success_url = reverse_lazy('view-courses')

    def get_courses_to_display(self):
        # TODO: Check and filter based on permissions/enrollment
        return Course.objects.all()

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['courses'] = self.get_courses_to_display()
        return context


class DeleteSemester(DeleteView):
    model = Semester
    context_object_name = 'semester'
    success_url = reverse_lazy('view-courses')
    template_name = 'autograder/delete_course.html'


class ShowSemesterDetail(View):
    TEMPLATE_NAME = 'autograder/semester_detail.html'

    def get(self, request, course_name):
        """
        View a Course and the Semesters that belong to it.
        """
        return render(request, ShowSemesterDetail.TEMPLATE_NAME,
                      self.get_context_starter(course_name))

    def post(self, request, course_name):
        """
        Add a new Semester to the Course.
        """
        try:
            Semester.objects.validate_and_create(
                name=request.POST['semester_name'],
                course=self.get_course(course_name))
            return HttpResponseRedirect(self.get_success_url(course_name))
        except ValidationError as e:
            context = self.get_context_starter(course_name)
            context['request'] = request.POST
            context['errors'] = e.message_dict
            context['non_field_errors'] = e.message_dict[NON_FIELD_ERRORS]
            return render(request, ShowSemesterDetail.TEMPLATE_NAME, context)

    def get_semester(self, course_name):
        return get_object_or_404(Course, name=course_name)

    def get_semesters_to_display(self, course):
        # TODO: Check and filter based on permissions/enrollment
        self.semesters_to_display = course.semesters.all()
        return self.semesters_to_display

    def get_success_url(self, course_name):
        return reverse_lazy('course-detail', args=[course_name])

    def get_context_starter(self, course_name):
        course = self.get_course(course_name)
        return {
            'course': course,
            'semesters': self.get_semesters_to_display(course),
            'errors': {}
        }
