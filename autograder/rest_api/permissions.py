from typing import Any, Callable, Type

from django.utils import timezone
from rest_framework import exceptions, permissions

import autograder.core.models as ag_models
from autograder.core.models.get_ultimate_submissions import get_ultimate_submissions


GetCourseFnType = Callable[[Any], ag_models.Course]
GetGroupFnType = Callable[[Any], ag_models.SubmissionGroup]
PermissionClassType = Type[permissions.BasePermission]


class IsReadOnly(permissions.BasePermission):
    def has_object_permission(self, request, view, obj):
        return request.method in permissions.SAFE_METHODS


def is_admin(get_course_fn: GetCourseFnType=lambda course: course) -> PermissionClassType:
    class IsAdmin(permissions.BasePermission):
        def has_object_permission(self, request, view, obj):
            course = get_course_fn(obj)
            return course.is_administrator(request.user)

    return IsAdmin


def is_staff(get_course_fn: GetCourseFnType=lambda course: course) -> PermissionClassType:
    class IsStaff(permissions.BasePermission):
        def has_object_permission(self, request, view, obj):
            course = get_course_fn(obj)
            return course.is_course_staff(request.user)

    return IsStaff


def is_handgrader(get_course_fn: GetCourseFnType=lambda course: course) -> PermissionClassType:
    class IsHandgrader(permissions.BasePermission):
        def has_object_permission(self, request, view, obj):
            course = get_course_fn(obj)
            return course.is_handgrader(request.user)

    return IsHandgrader


def is_admin_or_read_only_staff(
        get_course_fn: GetCourseFnType=lambda course: course) -> PermissionClassType:
    class IsAdminOrReadOnlyStaff(permissions.BasePermission):
        def has_object_permission(self, request, view, obj):
            course = get_course_fn(obj)
            is_read_only_staff = (request.method in permissions.SAFE_METHODS and
                                  course.is_course_staff(request.user))
            return course.is_administrator(request.user) or is_read_only_staff

    return IsAdminOrReadOnlyStaff


def can_view_project(
    get_project_fn: Callable[[Any], ag_models.Project]=lambda project: project
) -> Type[permissions.BasePermission]:
    class CanViewProject(permissions.BasePermission):
        def has_object_permission(self, request, view, obj):
            project = get_project_fn(obj)
            if (project.course.is_course_staff(request.user) or
                    project.course.is_handgrader(request.user)):
                return True

            if not project.visible_to_students:
                return False

            return project.course.is_enrolled_student(request.user) or project.guests_can_submit

    return CanViewProject


def is_staff_or_group_member(
    get_group_fn: GetGroupFnType=lambda group: group
) -> Type[permissions.BasePermission]:
    class IsStaffOrGroupMember(permissions.BasePermission):
        def has_object_permission(self, request, view, obj):
            group = get_group_fn(obj)
            return (group.project.course.is_course_staff(request.user) or
                    group.members.filter(pk=request.user.pk).exists())

    return IsStaffOrGroupMember


def is_group_member(get_group_fn: GetGroupFnType=lambda group: group) -> PermissionClassType:
    class IsGroupMember(permissions.BasePermission):
        def has_object_permission(self, request, view, obj):
            group = get_group_fn(obj)
            return group.members.filter(pk=request.user.pk).exists()

    return IsGroupMember


def can_request_feedback_category(
    get_submission_fn: Callable[[Any], ag_models.Submission]=lambda submission: submission
) -> Type[permissions.BasePermission]:
    class CanRequestFeedbackCategory(permissions.BasePermission):
        def has_object_permission(self, request, view, obj):
            try:
                fdbk_category = ag_models.FeedbackCategory(
                    request.query_params.get('feedback_category'))
            except KeyError:
                raise exceptions.ValidationError(
                    {'feedback_category': 'Missing required query param: feedback_category'})
            except ValueError:
                raise exceptions.ValidationError(
                    {'feedback_category': 'Invalid feedback category requested: {}'.format(
                        request.query_params.get('feedback_category'))})

            submission = get_submission_fn(obj)
            group = submission.submission_group
            project = group.project
            course = project.course
            deadline_past = _deadline_is_past(submission)

            is_group_member = group.members.filter(pk=request.user.pk).exists()
            if course.is_course_staff(request.user):
                # Staff can always request any feedback category for
                # their own submissions.
                if is_group_member:
                    return True

                # Staff can always request staff_viewer feedback
                # for other groups' submissions.
                if fdbk_category == ag_models.FeedbackCategory.staff_viewer:
                    return True

                # Staff can only request staff_viewer or max feedback
                # for other groups' submissions.
                if fdbk_category != ag_models.FeedbackCategory.max:
                    return False

                # Staff can only request max feedback for other groups'
                # ultimate submissions if the project deadline and group's
                # extension have passed.
                [group_ultimate_submission] = get_ultimate_submissions(project, group.pk)
                return deadline_past and group_ultimate_submission == submission

            # Non-staff users cannot view other groups' submissions
            if not group.members.filter(pk=request.user.pk).exists():
                return False

            if fdbk_category == ag_models.FeedbackCategory.normal:
                return not submission.is_past_daily_limit

            if fdbk_category == ag_models.FeedbackCategory.past_limit_submission:
                return submission.is_past_daily_limit

            if fdbk_category == ag_models.FeedbackCategory.ultimate_submission:
                [group_ultimate_submission] = get_ultimate_submissions(project, group.pk)
                return (not project.hide_ultimate_submission_fdbk and
                        group_ultimate_submission == submission and
                        deadline_past)

            return False

    return CanRequestFeedbackCategory


def _deadline_is_past(submission):
    now = timezone.now()
    group = submission.submission_group
    project = group.project
    if project.closing_time is None:
        return True

    if group.extended_due_date is None:
        return project.closing_time < now

    return group.extended_due_date < now
