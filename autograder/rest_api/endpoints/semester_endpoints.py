from django.contrib.auth.models import User
from django import http
from django.core.urlresolvers import reverse

from .endpoint_base import EndpointBase

from autograder.core.models import Course


class GetUpdateSemesterEndpoint(EndpointBase):
    pass


class ListAddRemoveSemesterStaffEndpoint(EndpointBase):
    pass


class ListAddUpdateRemoveEnrolledStudentsEndpoint(EndpointBase):
    pass


class ListAddProjectEndpoint(EndpointBase):
    pass


