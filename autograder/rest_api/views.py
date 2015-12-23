from autograder.core.models import Course, Semester
from autograder.rest_api.serializers import CourseSerializer, SemesterSerializer
from rest_framework import generics
from django.contrib.auth.models import User


class SemesterList(generics.ListCreateAPIView):
    queryset = Semester.objects.all()
    serializer_class = SemesterSerializer


class SemesterDetail(generics.RetrieveUpdateDestroyAPIView):
    queryset = Semester.objects.all()
    serializer_class = SemesterSerializer


class CourseList(generics.ListCreateAPIView):
    queryset = Course.objects.all()
    serializer_class = CourseSerializer


class CourseDetail(generics.RetrieveUpdateDestroyAPIView):
    queryset = Course.objects.all()
    serializer_class = CourseSerializer


# class RestAPIViewBase:
#     def get(self, request, **kwargs):
#         resources = self._fetch_resources(request)
#         has_permission = self._has_read_permission(request, resources)
#         if not has_permission:
#             # return 403
#             pass

#         return self._build_response(request, resources)

#     def post(self, request, **kwargs):
#         has_permission = self._has_create_permission(request)
#         if not has_permission:
#             # return 403
#             pass

#         created_resource = self._create_resource()

#     def patch(self, request, **kwargs):
#         resources = self._fetch_resources(request)
#         has_permission = self._has_update_permission(request, resources)
#         if not has_permission:
#             # return 403
#             pass


#     def delete(self, request, **kwargs):
#         pass

