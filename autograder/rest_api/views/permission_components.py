from django.utils import timezone
from rest_framework import permissions, exceptions


def is_admin_or_read_only_staff(request, course):
    is_admin = course.is_administrator(request.user)
    staff_and_read_only = (course.is_course_staff(request.user) and
                           request.method in permissions.SAFE_METHODS)
    return is_admin or staff_and_read_only


def user_can_view_project(user, project):
    if (project.course.is_administrator(user) or
            project.course.is_course_staff(user)):
        return True

    if not project.visible_to_students:
        return False

    if project.course.is_enrolled_student(user):
        return True

    return project.allow_submissions_from_non_enrolled_students


def user_can_view_group(user, group):
    if not user_can_view_project(user, group.project):
        return False

    if (group.project.course.is_administrator(user) or
            group.project.course.is_course_staff(user)):
        return True

    return group.members.filter(pk=user.pk).exists()


def user_can_request_feedback_type(user, feedback_type, submission):
    '''
    Returns True if the given user is allowed to request the specified
    type of feedback for the given submission.

    Notes for staff members:
        - Staff members can always request any feedback option for their
          own submission.
        - Staff members can only request 'staff_viewer' feedback for
          non-ultimate submissions belonging to other groups. Staff
          members can request max feedback for other groups' ultimate
          submissions as long as the deadline has passed for that group.

    Valid options for feedback type are:
        - 'normal'
        - 'ultimate_submission'
        - 'staff_viewer'
        - 'past_submission_limit'
        - 'max'
    '''
    group = submission.submission_group
    project = group.project
    course = project.course

    deadline_past = _deadline_is_past(submission)

    if course.is_course_staff(user):
        if (group.members.filter(pk=user.pk).exists() or
                feedback_type == 'staff_viewer'):
            return True

        if deadline_past and feedback_type == 'max':
            return True

        return False

    if not group.members.filter(pk=user.pk).exists():
        return False

    if feedback_type == 'normal':
        return not submission.is_past_daily_limit

    if feedback_type == 'ultimate_submission':
        return (not project.hide_ultimate_submission_fdbk and
                group.ultimate_submission == submission and
                deadline_past)

    if feedback_type == 'past_submission_limit':
        return submission.is_past_daily_limit

    if feedback_type == 'max' or feedback_type == 'staff_viewer':
        return False

    raise exceptions.ValidationError(
        {'feedback_type': 'Invalid feedback type requested: {}'.format(feedback_type)})


def _deadline_is_past(submission):
    now = timezone.now()
    group = submission.submission_group
    project = group.project
    if project.closing_time is None:
        return True

    if group.extended_due_date is None:
        return project.closing_time < now

    return group.extended_due_date < now
