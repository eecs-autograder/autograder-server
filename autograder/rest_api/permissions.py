from functools import singledispatch
from typing import Any, Callable, Type

from django.utils import timezone
from drf_composable_permissions.p import P
from rest_framework import exceptions, permissions

import autograder.core.models as ag_models
from autograder.core.models.get_ultimate_submissions import get_ultimate_submissions
from autograder.core.submission_feedback import AGTestPreLoader

GetCourseFnType = Callable[[ag_models.AutograderModel], ag_models.Course]
GetProjectFnType = Callable[[ag_models.AutograderModel], ag_models.Project]
GetGroupFnType = Callable[[ag_models.AutograderModel], ag_models.Group]
PermissionClassType = Type[permissions.BasePermission]


# Most of the functions that create permissions classes take in as an
# argument a function that returns the kind of object that the
# permissions class requires. For example, is_admin requires a Course,
# and therefore takes in a function that extracts the related course
# from whatever object it is given.
#
# For convenience, we define a set of function overloads that will
# handle common AG model types. These functions are set as the
# default argument where appropriate.


@singledispatch
def _get_course(model: ag_models.AutograderModel) -> ag_models.Course:
    if hasattr(model, 'project') and isinstance(model.project, ag_models.Project):
        return model.project.course

    raise NotImplementedError


@_get_course.register(ag_models.Course)
def _(course: ag_models.Course) -> ag_models.Course:
    return course


@_get_course.register(ag_models.Project)
def _(project: ag_models.Project) -> ag_models.Course:
    return project.course


@_get_course.register(ag_models.Group)
def _(group: ag_models.Group) -> ag_models.Course:
    return group.project.course


@_get_course.register(ag_models.Submission)
def _(submission: ag_models.Submission):
    return submission.group.project.course


@singledispatch
def _get_project(model: ag_models.AutograderModel) -> ag_models.Project:
    if hasattr(model, 'project') and isinstance(model.project, ag_models.Project):
        return model.project

    raise NotImplementedError


@_get_project.register(ag_models.Project)
def _(project: ag_models.Project) -> ag_models.Project:
    return project


@_get_project.register(ag_models.Group)
def _(group: ag_models.Group) -> ag_models.Project:
    return group.project


@_get_project.register(ag_models.Submission)
def _(submission: ag_models.Submission) -> ag_models.Project:
    return submission.group.project


@singledispatch
def _get_group(model: ag_models.AutograderModel) -> ag_models.Group:
    if hasattr(model, 'group') and isinstance(model.group, ag_models.Group):
        return model.group

    raise NotImplementedError


@_get_group.register(ag_models.Group)
def _(group: ag_models.Group) -> ag_models.Group:
    return group


class IsReadOnly(permissions.BasePermission):
    def has_object_permission(self, request, view, obj):
        return request.method in permissions.SAFE_METHODS


class IsSuperuser(permissions.BasePermission):
    def has_object_permission(self, request, view, obj):
        return request.user.is_superuser


def is_admin(get_course_fn: GetCourseFnType=_get_course) -> PermissionClassType:
    class IsAdmin(permissions.BasePermission):
        def has_object_permission(self, request, view, obj):
            course = get_course_fn(obj)
            return course.is_admin(request.user)

    return IsAdmin


def is_staff(get_course_fn: GetCourseFnType=_get_course) -> PermissionClassType:
    class IsStaff(permissions.BasePermission):
        def has_object_permission(self, request, view, obj):
            course = get_course_fn(obj)
            return course.is_staff(request.user)

    return IsStaff


def is_handgrader(get_course_fn: GetCourseFnType=_get_course) -> PermissionClassType:
    class IsHandgrader(permissions.BasePermission):
        def has_object_permission(self, request, view, obj):
            course = get_course_fn(obj)
            return course.is_handgrader(request.user)

    return IsHandgrader


def is_student(get_course_fn: GetCourseFnType=_get_course) -> PermissionClassType:
    class IsStudent(permissions.BasePermission):
        def has_object_permission(self, request, view, obj):
            course = get_course_fn(obj)
            return course.is_student(request.user)

    return IsStudent


def is_admin_or_handgrader_or_read_only_staff(
        get_course_fn: GetCourseFnType=_get_course) -> PermissionClassType:
    class IsAdminOrHandgraderOrReadOnlyStaff(permissions.BasePermission):
        def has_object_permission(self, request, view, obj):
            course = get_course_fn(obj)
            is_read_only_staff = (request.method in permissions.SAFE_METHODS
                                  and course.is_staff(request.user))
            return (course.is_admin(request.user) or course.is_handgrader(request.user)
                    or is_read_only_staff)

    return IsAdminOrHandgraderOrReadOnlyStaff


def is_admin_or_read_only_staff(
        get_course_fn: GetCourseFnType=_get_course) -> PermissionClassType:
    class IsAdminOrReadOnlyStaff(permissions.BasePermission):
        def has_object_permission(self, request, view, obj):
            course = get_course_fn(obj)
            is_read_only_staff = (request.method in permissions.SAFE_METHODS
                                  and course.is_staff(request.user))
            return course.is_admin(request.user) or is_read_only_staff

    return IsAdminOrReadOnlyStaff


def can_view_project(
    get_project_fn: GetProjectFnType=_get_project
) -> Type[permissions.BasePermission]:
    class CanViewProject(permissions.BasePermission):
        def has_object_permission(self, request, view, obj):
            project = get_project_fn(obj)
            if (project.course.is_staff(request.user)
                    or project.course.is_handgrader(request.user)):
                return True

            if not project.visible_to_students:
                return False

            return project.course.is_student(request.user) or project.guests_can_submit

    return CanViewProject


def is_admin_or_read_only_can_view_project(
    get_project_fn: GetProjectFnType=_get_project
) -> Type[permissions.BasePermission]:
    return (
        P(is_admin(lambda obj: get_project_fn(obj).course))
        | (P(IsReadOnly) & can_view_project(get_project_fn))
    )


def is_staff_or_group_member(
    get_group_fn: GetGroupFnType=_get_group
) -> Type[permissions.BasePermission]:
    class IsStaffOrGroupMember(permissions.BasePermission):
        def has_object_permission(self, request, view, obj):
            group = get_group_fn(obj)
            return (group.project.course.is_staff(request.user)
                    or group.members.filter(pk=request.user.pk).exists())

    return IsStaffOrGroupMember


def is_group_member(get_group_fn: GetGroupFnType=_get_group) -> PermissionClassType:
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
            group = submission.group
            project = group.project
            course = project.course
            deadline_past = _deadline_is_past(submission)

            ag_test_preloader = AGTestPreLoader(project)

            in_group = group.members.filter(pk=request.user.pk).exists()
            if course.is_staff(request.user):
                # Staff can always request any feedback category for
                # their own submissions.
                if in_group:
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
                [group_ultimate_submission] = get_ultimate_submissions(
                    project, group, ag_test_preloader=ag_test_preloader)
                return deadline_past and group_ultimate_submission == submission

            # Non-staff users cannot view other groups' submissions
            if not group.members.filter(pk=request.user.pk).exists():
                return False

            if fdbk_category == ag_models.FeedbackCategory.normal:
                return not submission.is_past_daily_limit

            if fdbk_category == ag_models.FeedbackCategory.past_limit_submission:
                return submission.is_past_daily_limit

            if fdbk_category == ag_models.FeedbackCategory.ultimate_submission:
                [group_ultimate_submission] = get_ultimate_submissions(
                    project, group, ag_test_preloader=ag_test_preloader)
                return (not project.hide_ultimate_submission_fdbk
                        and group_ultimate_submission == submission
                        and deadline_past)

            return False

    return CanRequestFeedbackCategory


def _deadline_is_past(submission):
    now = timezone.now()
    group = submission.group
    project = group.project
    if project.closing_time is None:
        return True

    if group.extended_due_date is None:
        return project.closing_time < now

    return group.extended_due_date < now
