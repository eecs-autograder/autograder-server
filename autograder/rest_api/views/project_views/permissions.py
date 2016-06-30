from rest_framework import permissions


class ProjectPermissions(permissions.BasePermission):
    def has_object_permission(self, request, view, project):
        if request.method not in permissions.SAFE_METHODS:
            return project.course.is_administrator(request.user)

        if project.course.is_course_staff(request.user):
            return True

        if not project.visible_to_students:
            return False

        if project.course.is_enrolled_student(request.user):
            return True

        return project.allow_submissions_from_non_enrolled_students
