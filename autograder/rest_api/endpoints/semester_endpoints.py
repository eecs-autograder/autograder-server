from django.contrib.auth.models import User
from django import http
from django.core.urlresolvers import reverse

from .endpoint_base import EndpointBase

from autograder.core.models import Course

DEFAULT_ENROLLED_STUDENT_PAGE_SIZE = 20


class GetUpdateSemesterEndpoint(EndpointBase):
    pass


class ListAddRemoveSemesterStaffEndpoint(EndpointBase):
    pass


class ListAddUpdateRemoveEnrolledStudentsEndpoint(EndpointBase):
    pass


class ListAddProjectEndpoint(EndpointBase):
    pass


