from django.core.exceptions import ObjectDoesNotExist
from django.http import (
    JsonResponse, HttpResponseForbidden, HttpResponseNotFound)

from autograder.frontend.json_api_serializers import (
    course_to_json, semester_to_json)
from autograder.frontend.frontend_utils import LoginRequiredView

from autograder.models import Course


class GetCourse(LoginRequiredView):
    def get(self, request, course_id):
        try:
            course = Course.objects.get(pk=course_id)
        except ObjectDoesNotExist:
            return HttpResponseNotFound()

        if not course.is_course_admin(self.request.user):
            return HttpResponseForbidden()

        response_content = {
            'data': course_to_json(course),
            'included': [
                {
                    'data': semester_to_json(
                        semester, all_fields=False,
                        user_is_semester_staff=True)
                }
                for semester in course.semesters.all().order_by('pk')
            ]
        }

        return JsonResponse(response_content)


class ListCourses(LoginRequiredView):
    """
    Reponse list content determinied by user permissions.
    """
    def get(self, request):
        courses = Course.get_courses_for_user(request.user)
        data = {
            'data': [
                course_to_json(course) for course in courses
            ]
        }

        return JsonResponse(data)


# Move superuser things to Django Admin page
# class AddCourse(ExceptionLoggingView):
#     """
#     Permissions required: Superuser
#     """
#     pass


# class AddCourseAdmin(ExceptionLoggingView):
#     """
#     Permissions required: Superuser
#     """
#     pass


# class RemoveCourseAdmin(ExceptionLoggingView):
#     """
#     Permissions required: Superuser
#     """
#     pass
