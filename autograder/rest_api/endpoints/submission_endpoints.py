from django.contrib.auth.models import User
from django import http
from django.core.urlresolvers import reverse

from .endpoint_base import EndpointBase

from autograder.core.models import Submission


class GetSubmissionEndpoint(EndpointBase):
    pass


class ListSubmittedFilesEndpoint(EndpointBase):
    pass


class GetSubmittedFileEndpoint(EndpointBase):
    pass


class ListAutograderTestCaseResultsEndpoint(EndpointBase):
    pass


class ListStudentTestSuiteResultsEndpoint(EndpointBase):
    pass

