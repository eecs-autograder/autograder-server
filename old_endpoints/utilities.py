from django.core import exceptions


def check_can_view_project(user, project):
    if project.semester.is_semester_staff(user):
        return

    if not project.visible_to_students:
        raise exceptions.PermissionDenied()

    if project.semester.is_enrolled_student(user):
        return

    if not project.allow_submissions_from_non_enrolled_students:
        raise exceptions.PermissionDenied()


def check_is_group_member(user, group):
    if not user.groups_is_member_of.filter(pk=group.pk).exists():
        raise exceptions.PermissionDenied()


def check_can_view_group(user, group):
    if group.project.semester.is_semester_staff(user):
        return

    check_is_group_member(user, group)
