import os
import json

from django.contrib.auth.models import User
from django.core.exceptions import ValidationError, ObjectDoesNotExist
from django.http import (
    HttpResponse, JsonResponse, HttpResponseForbidden, HttpResponseNotFound,
    HttpResponseBadRequest, FileResponse)

from autograder.frontend.frontend_utils import LoginRequiredView
from autograder.frontend.json_api_serializers import (
    submission_to_json, submission_group_to_json)

from autograder.models import SubmissionGroup, Project, Submission
from autograder.models.fields import FeedbackConfiguration


class SubmissionRequestHandler(LoginRequiredView):
    _EDITABLE_FIELDS = [
        'test_case_feedback_config_override',
        'show_all_test_cases'
    ]

    def post(self, request):
        """
        POST dictionary parameters: 'submission_group_id'
        FILES key: 'files'
        """
        files = request.FILES.getlist('files')
        try:
            group = SubmissionGroup.objects.get(
                pk=request.POST['submission_group_id'])
        except KeyError:
            return HttpResponseBadRequest()
        except ObjectDoesNotExist:
            return HttpResponseNotFound()

        username = request.user.username
        if username not in group.members:
            return HttpResponseForbidden()

        is_staff = group.project.semester.is_semester_staff(
            request.user.username)
        feedback_override = (
            FeedbackConfiguration.get_max_feedback() if is_staff else None)

        submission = Submission.objects.validate_and_create(
            submitted_files=files, submission_group=group,
            test_case_feedback_config_override=feedback_override)

        # TODO: add to task queue

        response_content = {
            'data': submission_to_json(submission)
        }

        return JsonResponse(response_content, status=201)

    def get(self, request, submission_id):
        try:
            submission = Submission.objects.get(pk=submission_id)
        except ObjectDoesNotExist:
            return HttpResponseNotFound()

        username = request.user.username
        semester = submission.submission_group.project.semester
        is_staff = semester.is_semester_staff(username)
        is_member = username in submission.submission_group.members
        if not is_member and not is_staff:
            return HttpResponseForbidden()

        feedback_override = (
            FeedbackConfiguration.get_max_feedback() if is_staff else None)

        if submission.show_all_test_cases or (is_staff and is_member):
            result_set = submission.results.all()
        else:
            result_set = submission.results.filter(
                test_case__hide_from_students=False)

        response_content = {
            'data': submission_to_json(submission),
            'meta': {
                'results': [
                    result.to_json(override_feedback=feedback_override) for
                    result in result_set
                ]
            }
        }

        return JsonResponse(response_content, status=200)

    def patch(self, request, submission_id):
        try:
            submission = Submission.objects.get(pk=submission_id)
        except ObjectDoesNotExist:
            return HttpResponseNotFound()

        course = submission.submission_group.project.semester.course
        if not course.is_course_admin(request.user):
            return HttpResponseForbidden()

        request_content = json.loads(request.body.decode('utf-8'))
        to_edit = request_content['data']['attributes']

        for field_name in SubmissionRequestHandler._EDITABLE_FIELDS:
            if field_name in to_edit:
                setattr(submission, field_name, to_edit[field_name])

        try:
            submission.validate_and_save()
        except ValidationError as e:
            return JsonResponse(
                {'errors': {'meta': e.message_dict}}, status=400)

        return HttpResponse(status=204)


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

        return FileResponse(matches[0])
