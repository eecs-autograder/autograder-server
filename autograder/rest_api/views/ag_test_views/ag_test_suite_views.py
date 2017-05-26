from rest_framework import viewsets, mixins, permissions

import autograder.core.models as ag_models
import autograder.rest_api.serializers as ag_serializers
from autograder.rest_api import transaction_mixins

from ..load_object_mixin import build_load_object_mixin


class AGTestSuitesViewSet(build_load_object_mixin(ag_models.ag))
