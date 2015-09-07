import json

from django.contrib.auth.models import User
from django.core.exceptions import ValidationError, ObjectDoesNotExist
from django.http import (
    HttpResponse, JsonResponse, HttpResponseForbidden, HttpResponseNotFound,
    HttpResponseBadRequest)

from autograder.frontend.frontend_utils import LoginRequiredView
from autograder.frontend.json_api_serializers import (
    submission_group_to_json, submission_to_json)

from autograder.models import SubmissionGroup, Project


class SubmissionGroupRequestHandler(LoginRequiredView):
    _EDITABLE_FIELDS = ['extended_due_date']

    def post(self, request):
        request_content = json.loads(request.body.decode('utf-8'))
        project_id = (
            request_content['data']['relationships']['project']['data']['id'])
        try:
            project = Project.objects.get(pk=project_id)
        except ObjectDoesNotExist:
            return HttpResponseNotFound()

        usernames = request_content['data']['attributes']['members']
        if not usernames:
            return HttpResponse(
                'At least one user must be specified', status=409)

        if (not project.semester.course.is_course_admin(request.user) and
                request.user.username not in usernames):
            return HttpResponseForbidden()

        users = [User.objects.get_or_create(username=username)[0]
                 for username in usernames]
        try:
            new_group = SubmissionGroup.objects.validate_and_create(
                members=[user.username for user in users], project=project)
        except ValidationError as e:
            return JsonResponse(
                {'errors': {'meta': e.message_dict}}, status=409)

        response_content = {
            'data': submission_group_to_json(new_group)
        }
        return JsonResponse(response_content, status=201)

    def get(self, request, submission_group_id=None):
        """
        If a submission_group_id is not provided, then the submission group
        can be looked up with the following query string
        parameters: project_id, username
        """
        try:
            if submission_group_id is None:
                group = self._get_by_query_params(request)
            else:
                group = SubmissionGroup.objects.get(pk=submission_group_id)
        except ObjectDoesNotExist:
            return HttpResponseNotFound()
        except KeyError:
            return HttpResponse(status=400)

        if (request.user.username not in group.members and
                not group.project.semester.is_semester_staff(request.user)):
            return HttpResponseForbidden()

        is_admin = group.project.semester.course.is_course_admin(
            request.user)
        response_content = {
            'data': submission_group_to_json(group),
            'included': [
                submission_to_json(submission, all_fields=False)
                for submission in group.submissions.all().order_by('-_timestamp')
            ],
            'meta': {
                'permissions': {
                    'can_delete': is_admin,
                    'can_edit': is_admin
                }
            }
        }

        return JsonResponse(response_content, status=200)

    def _get_by_query_params(self, request):
        project_id = request.GET['project_id']
        project = Project.objects.get(pk=project_id)
        usernames = request.GET.getlist('usernames')

        group = SubmissionGroup.get_group(usernames, project)
        return group

    # -------------------------------------------------------------------------

    def patch(self, request, submission_group_id):
        try:
            group = SubmissionGroup.objects.get(pk=submission_group_id)
        except ObjectDoesNotExist:
            return HttpResponseNotFound()

        if not group.project.semester.course.is_course_admin(request.user):
            return HttpResponseForbidden()

        request_content = json.loads(request.body.decode('utf-8'))
        to_edit = request_content['data']['attributes']
        for field in SubmissionGroupRequestHandler._EDITABLE_FIELDS:
            if field in to_edit:
                setattr(group, field, to_edit[field])

        try:
            group.validate_and_save()
            return HttpResponse(status=204)
        except ValidationError as e:
            return JsonResponse({'errors': {'meta': e.message_dict}})

    # def delete(self, request, submission_group_id):
    #     pass
