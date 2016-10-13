from rest_framework import permissions


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
          submissions.

    Note that staff members for the course that the submission belongs
    to are allowed to request any

    Valid options for feedback type are:
        - 'normal'
        - 'ultimate_submission'
        - 'staff_viewer'
        - 'past_limit_submission'
        - 'max'
    '''
    pass
