import os

from collections import namedtuple

from django.contrib.auth.models import User
from django.core.exceptions import ValidationError
from django.core.files.uploadedfile import SimpleUploadedFile

from autograder.tests.temporary_filesystem_test_case import (
    TemporaryFilesystemTestCase)

from autograder.models import (
    Course, Semester, Project, Submission, SubmissionGroup)

import autograder.shared.utilities as ut

import autograder.tests.dummy_object_utils as obj_ut
