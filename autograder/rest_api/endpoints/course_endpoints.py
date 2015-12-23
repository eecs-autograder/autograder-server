from django.contrib.auth.models import User
from django import http
from django.core.urlresolvers import reverse

from .endpoint_base import EndpointBase

from autograder.core.models import Course


class ListCreateCourseEndpoint(EndpointBase):
    pass


class GetUpdateCourseEndpoint(EndpointBase):
    pass


class ListAddRemoveCourseAdministratorsEndpoint(EndpointBase):
    pass


class ListAddSemesterEndpoint(EndpointBase):
    pass
