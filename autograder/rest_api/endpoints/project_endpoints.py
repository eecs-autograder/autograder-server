from django.contrib.auth.models import User
from django import http
from django.core.urlresolvers import reverse

from .endpoint_base import EndpointBase

from autograder.core.models import Course

DEFAULT_SUBMISSION_GROUP_PAGE_SIZE = 20


class GetUpdateProjectEndpoint(EndpointBase):
    pass


class ListAddProjectFileEndpoint(EndpointBase):
    pass


class GetUpdateDeleteProjectFileEndpoint(EndpointBase):
    pass


class ListAddAutograderTestCaseEndpoint(EndpointBase):
    pass


class ListAddStudentTestSuiteEndpoint(EndpointBase):
    pass


class ListAddSubmissionGroupEndpoint(EndpointBase):
    pass


class ListAddSubmissionGroupInvitationEndpoint(EndpointBase):
    pass


