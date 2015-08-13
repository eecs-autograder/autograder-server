import json

from django.contrib.auth.models import User
from django.core.exceptions import ValidationError, ObjectDoesNotExist
from django.http import (
    HttpResponse, JsonResponse, HttpResponseForbidden, HttpResponseNotFound,
    HttpResponseBadRequest)

from autograder.frontend.frontend_utils import LoginRequiredView
from autograder.frontend.json_api_serializers import submission_group_to_json

from autograder.models import SubmissionGroup, Project, Submission


class SubmissionRequestHandler(LoginRequiredView):
    _EDITABLE_FIELDS = []


class SubmittedFileRequestHandler(LoginRequiredView):
    pass
