from django.db.models.signals import post_save
from django.dispatch import receiver
from rest_framework import permissions

import autograder.core.models as ag_models
import autograder.rest_api.serializers as ag_serializers

from autograder.rest_api.views.ag_model_views import ListCreateNestedModelView


class IsAdminOrReadOnlyStaffOrStudent(permissions.BasePermission):
    def has_object_permission(self, request, view, course):
        is_admin = course.is_administrator(request.user)
        is_staff = course.is_course_staff(request.user)
        read_only = request.method in permissions.SAFE_METHODS
        is_enrolled = course.is_enrolled_student(request.user)
        is_handgrader = course.is_handgrader(request.user)

        return is_admin or (read_only and (is_staff or is_enrolled or is_handgrader))


class ListCreateProjectView(ListCreateNestedModelView):
    serializer_class = ag_serializers.ProjectSerializer
    permission_classes = (IsAdminOrReadOnlyStaffOrStudent,)

    model_manager = ag_models.Course.objects
    foreign_key_field_name = 'course'
    reverse_foreign_key_field_name = 'projects'

    def get_queryset(self):
        queryset = super().get_queryset()
        if self.request.method not in permissions.SAFE_METHODS:
            return queryset

        course = self.get_object()
        if course.is_enrolled_student(self.request.user) or course.is_handgrader(self.request.user):
            return queryset.filter(visible_to_students=True)

        return queryset


@receiver(post_save, sender=ag_models.Project)
def on_project_created(sender, instance, created, **kwargs):
    import sys
    if len(sys.argv) > 1 and sys.argv[1] == 'test':
        return

    if not created:
        return

    from autograder.grading_tasks.tasks import register_project_queues

    from autograder.celery import app
    register_project_queues.apply_async(
        kwargs={'project_pks': [instance.pk]}, queue='small_tasks',
        connection=app.connection())
