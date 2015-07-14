from django.views.generic.base import View
from django.views.generic.edit import CreateView, DeleteView

from django.core.exceptions import ValidationError
from django.forms.forms import NON_FIELD_ERRORS

from django.shortcuts import get_object_or_404, render

from django.template import RequestContext
from django.core.urlresolvers import reverse_lazy
from django.http import HttpResponseRedirect

from autograder.models import Course, Semester, Project


class AllCoursesView(CreateView):
    template_name = 'autograder/course_list.html'
    model = Course
    fields = ['name']
    success_url = reverse_lazy('course-list')

    def get_courses_to_display(self):
        # TODO: Check and filter based on permissions/enrollment
        return Course.objects.all()

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['courses'] = self.get_courses_to_display()
        return context


class DeleteCourse(DeleteView):
    model = Course
    context_object_name = 'course'
    success_url = reverse_lazy('course-list')
    template_name = 'autograder/delete_course.html'


class SingleCourseView(View):
    TEMPLATE_NAME = 'autograder/course_detail.html'

    def get(self, request, course_name):
        """
        View a Course and the Semesters that belong to it.
        """
        return render(request, SingleCourseView.TEMPLATE_NAME,
                      self.get_context_starter(course_name))

    def post(self, request, course_name):
        """
        Add a new Semester to the Course.
        """
        try:
            # TODO: csrf check
            Semester.objects.validate_and_create(
                name=request.POST['semester_name'],
                course=self.get_course(course_name))

            success_url = reverse_lazy('course-detail', args=[course_name])
            return HttpResponseRedirect(success_url)
        except ValidationError as e:
            context = self.get_context_starter(course_name)
            context['request'] = request.POST
            context['errors'] = e.message_dict
            print(context['errors'])
            context['non_field_errors'] = e.message_dict.get(
                NON_FIELD_ERRORS, {})

            context = RequestContext(self.request, context)
            return render(request, SingleCourseView.TEMPLATE_NAME, context)

    def get_course(self, course_name):
        return get_object_or_404(Course, name=course_name)

    def get_semesters_to_display(self, course):
        # TODO: Check and filter based on permissions/enrollment
        self.semesters_to_display = course.semesters.all()
        return self.semesters_to_display

    def get_context_starter(self, course_name):
        course = self.get_course(course_name)
        return {
            'course': course,
            'semesters': self.get_semesters_to_display(course),
            'errors': {},
            'non_field_errors': {}
        }


# -----------------------------------------------------------------------------
# -----------------------------------------------------------------------------

def _get_semester(course_name, semester_name):
    return get_object_or_404(
        Semester, name=semester_name, course__name=course_name)


class DeleteSemester(View):
    TEMPLATE_NAME = 'autograder/delete_semester.html'

    def get(self, request, course_name, semester_name):
        semester = _get_semester(course_name, semester_name)
        return render(
            request, DeleteSemester.TEMPLATE_NAME,
            RequestContext(request, {'semester': semester}))

    def post(self, request, course_name, semester_name):
        # TODO: csrf check
        semester = _get_semester(course_name, semester_name)
        semester.delete()
        return HttpResponseRedirect(
            reverse_lazy('course-detail', args=[course_name]))


class SemesterView(View):
    TEMPLATE_NAME = 'autograder/semester_detail.html'

    def get(self, request, course_name, semester_name):
        """
        View a Semester and Projects that belong to it.
        """
        context = self.get_context_starter(course_name, semester_name)
        return render(request, SemesterView.TEMPLATE_NAME, context)

    def post(self, request, course_name, semester_name):
        try:
            # TODO: csrf
            Project.objects.validate_and_create(
                name=request.POST['project_name'],
                semester=_get_semester(course_name, semester_name))

            success_url = reverse_lazy(
                'semester-detail', args=[course_name, semester_name])
            return HttpResponseRedirect(success_url)
        except ValidationError as e:
            context = self.get_context_starter(course_name, semester_name)
            context['request'] = request.POST
            context['errors'] = e.message_dict
            context['non_field_errors'] = e.message_dict.get(
                NON_FIELD_ERRORS, {})
            context = RequestContext(self.request, context)
            return render(request, SemesterView.TEMPLATE_NAME, context)

    def get_context_starter(self, course_name, semester_name):
        semester = _get_semester(course_name, semester_name)
        return {
            'course': semester.course,
            'semester': semester,
            'projects': semester.projects.all(),
            'errors': {},
            'non_field_errors': {}
        }


# -----------------------------------------------------------------------------
# -----------------------------------------------------------------------------

def _get_project(course_name, semester_name, project_name):
    semester = _get_semester(course_name, semester_name)
    return get_object_or_404(
        Project, name=project_name, semester=semester)


class DeleteProject(View):
    TEMPLATE_NAME = 'autograder/delete_project.html'

    def get(self, request, course_name, semester_name, project_name):
        project = _get_project(course_name, semester_name, project_name)
        return render(
            request, DeleteProject.TEMPLATE_NAME,
            RequestContext(request, {'project': project}))

    def post(self, request, course_name, semester_name, project_name):
        # TODO: csrf
        project = _get_project(course_name, semester_name, project_name)
        print(project.name)
        project.delete()
        return HttpResponseRedirect(
            reverse_lazy('semester-detail', args=[course_name, semester_name]))


class ProjectView(View):
    TEMPLATE_NAME = 'autograder/project_detail.html'

    def get(self, request, course_name, semester_name, project_name):
        return render(
            request, ProjectView.TEMPLATE_NAME,
            self.get_context_starter(course_name, semester_name, project_name))

    # def post(self, request, course_name, semester_name, project_name):
    #     pass

    def get_context_starter(self, course_name, semester_name, project_name):
        project = _get_project(course_name, semester_name, project_name)
        return {
            'course': project.semester.course,
            'semester': project.semester,
            'project': project,
            'autograder_test_cases': project.autograder_test_cases.all(),
            'errors': {},
            'non_field_errors': {}
        }
