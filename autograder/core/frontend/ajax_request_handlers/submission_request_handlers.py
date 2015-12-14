import os
import json

# import logging
# logger = logging.getLogger(__name__)

from django.db import transaction
from django.db.models import Q
# from django.contrib.auth.models import User
from django.core.exceptions import ValidationError, ObjectDoesNotExist
from django.http import (
    HttpResponse, JsonResponse, HttpResponseForbidden, HttpResponseNotFound,
    HttpResponseBadRequest)
from django.utils import timezone

from autograder.core.frontend.frontend_utils import LoginRequiredView
from autograder.core.frontend.json_api_serializers import (
    submission_to_json)

from autograder.core.models import SubmissionGroup, Submission

import autograder.core.shared.feedback_configuration as fbc


class SubmissionRequestHandler(LoginRequiredView):
    def post(self, request):
        """
        POST dictionary parameters: 'submission_group_id'
        FILES key: 'files'
        """
        timestamp = timezone.now()
        files = request.FILES.getlist('files')
        try:
            group = SubmissionGroup.objects.get(
                pk=request.POST['submission_group_id'])
        except KeyError:
            return HttpResponseBadRequest()
        except ObjectDoesNotExist:
            return HttpResponseNotFound('Submission group not found')

        username = request.user.username
        if username not in group.members:
            return HttpResponseForbidden()

        error_message = None
        if group.project.semester.is_semester_staff(group.members[0]):
            pass
        elif self._deadline_passed(group, timestamp):
            error_message = "The deadline for this project has passed"
        elif group.project.disallow_student_submissions:
            error_message = (
                'Submissions are currently disabled for this project')

        if error_message:
            return JsonResponse(
                {'errors': {'meta': error_message}}, status=409)

        submission = None
        with transaction.atomic():
            group = SubmissionGroup.objects.select_for_update().get(
                pk=group.pk)

            if self._user_has_active_submission(group, timestamp):
                msg = (
                    'You currently have a submission being processed. '
                    'Please wait until it is finished before submitting again.'
                )
                return JsonResponse(
                    {'errors': {'meta': msg}}, status=409)

            submission = Submission.objects.validate_and_create(
                submitted_files=files, submission_group=group,
                timestamp=timestamp)

        response_content = {
            'data': submission_to_json(submission)
        }

        return JsonResponse(response_content, status=201)

    def _deadline_passed(self, group, timestamp):
        if group.extended_due_date is not None:
            deadline = group.extended_due_date
        else:
            deadline = group.project.closing_time

        if deadline is None:
            return False

        if timestamp > deadline:
            return True

    def _user_has_active_submission(self, group, timestamp):
        return Submission.objects.filter(
            submission_group=group
        ).filter(
            Q(status=Submission.GradingStatus.received) |
            Q(status=Submission.GradingStatus.queued) |
            Q(status=Submission.GradingStatus.being_graded))

    def get(self, request, submission_id):
        try:
            submission = Submission.objects.get(pk=submission_id)
        except ObjectDoesNotExist:
            return HttpResponseNotFound()

        username = request.user.username
        group = submission.submission_group
        semester = group.project.semester
        is_staff = semester.is_semester_staff(username)
        is_member = username in group.members
        if not is_member and not is_staff:
            return HttpResponseForbidden()

        feedback_override = (
            fbc.AutograderTestCaseFeedbackConfiguration.get_max_feedback()
            if is_staff else None)
        suite_feedback_override = (
            fbc.StudentTestSuiteFeedbackConfiguration.get_max_feedback()
            if is_staff else None)

        # TODO: post deadline test revealing
        if (  # submission.show_all_test_cases_and_suites or
                (is_staff and is_member)):
            result_set = submission.results.all()
            suite_result_set = submission.suite_results.all()
        else:
            result_set = submission.results.filter(
                test_case__feedback_configuration__visibility_level=(
                    fbc.VisibilityLevel.show_to_students.value))  # TODO: abstract away this query
            suite_result_set = submission.suite_results.filter(
                test_suite__feedback_configuration__visibility_level=(
                    fbc.VisibilityLevel.show_to_students.value))  # TODO: abstract away this query

        results_json = [
            result.to_json(override_feedback=feedback_override) for
            result in result_set
        ]

        suite_results_json = [
            result.to_json(
                feedback_config_override=suite_feedback_override)
            for result in suite_result_set
        ]

        response_content = {
            'data': submission_to_json(submission),
            'meta': {
                'results': results_json,
                'suite_results': suite_results_json
            }
        }

        # logger.info('response_content: {}'.format(response_content))

        # if feedback_override is not None:
        #     points_feedback = feedback_override.points_feedback_level
        # else:
        #     points_feedback = (group.project.test_case_feedback_configuration.
        #                        points_feedback_level)

        # if suite_feedback_override is not None:
        #     suite_points_feedback = (
        #         suite_feedback_override.points_feedback_level)
        # elif (submission.student_test_suite_feedback_config_override
        #         is not None):
        #     suite_points_feedback = (
        #         submission.student_test_suite_feedback_config_override.
        #         points_feedback_level)
        # else:
        #     suite_points_feedback = (
        #         group.project.student_test_suite_feedback_configuration.
        #         points_feedback_level)

        # show_test_points = points_feedback != fbc.PointsFeedbackLevel.hide
        # show_suite_points = (
        #     suite_points_feedback != fbc.PointsFeedbackLevel.hide)

        # if not show_test_points and not show_suite_points:
        #     return JsonResponse(response_content, status=200)

        # if show_test_points:
        test_points_awarded = sum(
            result.get('total_points_awarded', 0) for result in results_json)
        test_points_possible = sum(
            result.get('total_points_possible', 0) for result in results_json)
        # else:
        #     test_points_awarded = 0
        #     test_points_possible = 0

        # if show_suite_points:
        suite_points_awarded = sum(
            result.get('points_awarded', 0) for result in suite_results_json)
        suite_points_possible = sum(
            result.get('points_possible', 0) for result in suite_results_json)
        # else:
        #     suite_points_awarded = 0
        #     suite_points_possible = 0

        total_score = test_points_awarded + suite_points_awarded
        points_possible = test_points_possible + suite_points_possible

        if points_possible != 0:
            response_content['meta']['total_points_awarded'] = total_score
            response_content['meta']['total_points_possible'] = points_possible

        return JsonResponse(response_content, status=200)

    # def patch(self, request, submission_id):
    #     try:
    #         submission = Submission.objects.get(pk=submission_id)
    #     except ObjectDoesNotExist:
    #         return HttpResponseNotFound()

    #     course = submission.submission_group.project.semester.course
    #     if not course.is_course_admin(request.user):
    #         return HttpResponseForbidden()

    #     request_content = json.loads(request.body.decode('utf-8'))
    #     to_edit = request_content['data']['attributes']

    #     for field_name in SubmissionRequestHandler._EDITABLE_FIELDS:
    #         if field_name in to_edit:
    #             setattr(submission, field_name, to_edit[field_name])

    #     try:
    #         submission.validate_and_save()
    #     except ValidationError as e:
    #         return JsonResponse(
    #             {'errors': {'meta': e.message_dict}}, status=400)

    #     return HttpResponse(status=204)


class SubmittedFileRequestHandler(LoginRequiredView):
    def get(self, request, submission_id, filename):
        try:
            submission = Submission.objects.get(pk=submission_id)
        except ObjectDoesNotExist:
            return HttpResponseNotFound()

        semester = submission.submission_group.project.semester
        is_staff = semester.is_semester_staff(request.user)
        is_member = (
            request.user.username in submission.submission_group.members)

        if not is_member and not is_staff:
            return HttpResponseForbidden()

        matches = list(filter(
            lambda file_: os.path.basename(file_.name) == filename,
            submission.submitted_files))
        if not matches:
            return HttpResponseNotFound()

        return HttpResponse(matches[0], content_type='text/plain')
