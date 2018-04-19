from rest_framework import permissions


class IsAdminOrReadOnlyStaff(permissions.BasePermission):
    def has_object_permission(self, request, view, course):
        is_admin = course.is_admin(request.user)
        staff_and_read_only = (course.is_staff(request.user) and
                               request.method in permissions.SAFE_METHODS)
        return is_admin or staff_and_read_only
