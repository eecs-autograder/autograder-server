from rest_framework import permissions

from ..permission_components import is_admin_or_read_only_staff, user_can_view_project


class ProjectPermissions(permissions.BasePermission):
    def has_object_permission(self, request, view, project):
        if request.method not in permissions.SAFE_METHODS:
            return project.course.is_administrator(request.user)

        return user_can_view_project(request.user, project)


class IsAdminOrReadOnlyStaff(permissions.BasePermission):
    def has_object_permission(self, request, view, project):
        return is_admin_or_read_only_staff(request, project.course)
