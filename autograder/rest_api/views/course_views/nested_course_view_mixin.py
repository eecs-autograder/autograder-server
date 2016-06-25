import autograder.core.models as ag_models


class NestedCourseViewMixin:
    def load_course(self):
        course = ag_models.Course.objects.get(pk=self.kwargs['course_pk'])
        self.check_object_permissions(self.request, course)
        return course
