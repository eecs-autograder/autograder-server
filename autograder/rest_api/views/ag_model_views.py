from typing import Optional, List

from django.core.exceptions import ObjectDoesNotExist
from django.http import Http404
from django.shortcuts import get_object_or_404
from rest_framework import viewsets, permissions, mixins, generics, response, status
from rest_framework.request import Request
from rest_framework.views import APIView

from autograder.rest_api.views.schema_generation import AGModelViewAutoSchema, \
    NestedModelViewAutoSchema, APITags
from ..transaction_mixins import (
    TransactionCreateMixin, TransactionPartialUpdateMixin,
    TransactionDestroyMixin)


class GetObjectLockOnUnsafeMixin:
    """
    This mixin for Django REST Framework view classes provides
    a get_object() method that calls select_for_update()
    on the queryset used to load the object.

    Class attributes:
        pk_key -- The key used to lookup the primary key
                  of the object to load. Defaults to 'pk'.
        model_manager -- The Django model manager used
            to look up the object. This attribute should
            be set in classes that inherit from this mixin.
    """

    pk_key = 'pk'
    model_manager = None

    def get_object(self, *, pk_override=None, model_manager_override=None):
        """
        :param pk_override: When specified, looks up the object
        with this specified primary key rather than getting the
        pk from the url.
        :return: Loads an object from the database using model_manager
        to perform the query. Http404 or PermissionDenied may be raised
        as in the Django REST Framework version of this method.
        """
        if self.model_manager is None and model_manager_override is None:
            raise ValueError('"model_manager" must not be None.')

        queryset = (model_manager_override if model_manager_override is not None
                    else self.model_manager)
        if self.request.method not in permissions.SAFE_METHODS:
            queryset = queryset.select_for_update()

        pk = pk_override if pk_override is not None else self.kwargs[self.pk_key]

        obj = get_object_or_404(queryset, pk=pk)
        self.check_object_permissions(self.request, obj)
        return obj


class AlwaysIsAuthenticatedMixin:
    """
    Provides a version of get_permissions() that appends
    IsAuthenticated to the view's permission classes.
    """
    def get_permissions(self):
        return [permissions.IsAuthenticated()] + super().get_permissions()


class AGModelAPIView(GetObjectLockOnUnsafeMixin, AlwaysIsAuthenticatedMixin, APIView):
    """
    A derived class of APIView that inherits from the mixins
    GetObjectLockOnUnsafeMixin and AlwaysIsAuthenticatedMixin.
    """
    pass


class AGModelGenericViewSet(GetObjectLockOnUnsafeMixin,
                            AlwaysIsAuthenticatedMixin,
                            viewsets.GenericViewSet):
    """
    A derived class of GenericViewSet that inherits from the mixins
    GetObjectLockOnUnsafeMixin and AlwaysIsAuthenticatedMixin.
    """
    swagger_schema = AGModelViewAutoSchema

    # Tags to apply to all operations in this view.
    # This can be overridden on individual operations by passing
    # 'api_tags' to @swagger_auto_schema
    api_tags = None  # type: Optional[List[APITags]]


class AGModelGenericView(GetObjectLockOnUnsafeMixin,
                         AlwaysIsAuthenticatedMixin,
                         generics.GenericAPIView):
    """
    A derived class of GenericAPIView that inherits from the mixins
    GetObjectLockOnUnsafeMixin and AlwaysIsAuthenticatedMixin.
    """
    pass


class NestedModelViewSet(GetObjectLockOnUnsafeMixin,
                         AlwaysIsAuthenticatedMixin,
                         generics.GenericAPIView):
    """
    A generic view set used for defining nested endpoints
    (one level of nesting only).

    This allows Django REST Framework's object-level permission checking
    to examine the -to-one (foreign) object when requesting
    the -to-many or -to-one (related) objects or creating a new related
    object.

    See mixin classes ListNestedModelMixin and CreateNestedModelMixin
    for more details and examples.

    NOTE: Do NOT use Django Rest Framework permissions classes with
    this kind of view set, as those classes may not have overridden
    has_object_permissions() as needed.
    """

    swagger_schema = NestedModelViewAutoSchema

    reverse_to_one_field_name = None

    def get_queryset(self):
        if self.reverse_to_one_field_name is None:
            raise ValueError('"reverse_to_one_field_name" must not be None.')

        return getattr(self.get_object(), self.reverse_to_one_field_name).all()


class ListNestedModelMixin(mixins.ListModelMixin):
    """
    Provides 'list' functionality when mixed with a NestedModelViewSet.

    For example, setting
    NestedModelViewSet.reverse_foreign_key_field_name to
    'projects' could allow the following:
        A GET request to /courses/2/projects/ could return a list of
        Projects that belong to Course 2, but only if the user is staff
        for or enrolled in that Course.

    NOTE: Do NOT mix ListNestedModelMixin with RetrieveNestedModelMixin,
    as the GET implementations will interfere.
    """

    def get(self, request, *args, **kwargs):
        return self.list(request, *args, **kwargs)


class RetrieveNestedModelMixin(mixins.RetrieveModelMixin):
    """
    Provides 'retrieve' functionality when mixed with a
    NestedModelViewSet.

    For example, setting
    NestedModelViewSet.reverse_one_to_one_field_name to
    'handgrading_rubric' could allow the following:
        A GET request to /project/2/handgrading_rubric/ returns the
        designated Project 2's handgrading rubric, but only if the user
        is staff for or enrolled in Project 2's Course.

    NOTE: Do NOT mix ListNestedModelMixin with RetrieveNestedModelMixin,
    as the GET implementations will interfere.
    """

    def get(self, request, *args, **kwargs):
        return self.retrieve(request, *args, **kwargs)

    def retrieve(self, *args, **kwargs):
        if self.reverse_to_one_field_name is None:
            raise ValueError('"reverse_to_one_field_name" must not be None.')

        instance = getattr(self.get_object(), self.reverse_to_one_field_name)
        serializer = self.get_serializer(instance)
        return response.Response(serializer.data)


class CreateNestedModelViewSet(TransactionCreateMixin):
    """
    Provides 'create' functionality when mixed with a
    NestedModelViewSet.

    For example, setting CreateNestedModelViewSet.one_to_one_field_name
    to 'project' could allow the following:
        A POST request to /courses/2/projects/ would create a new
        Project that belongs to Course 2 (overriding any 'course' field
        erroneously included in the request body), but only if the user
        is admin for that Course.
    """

    to_one_field_name = None

    def perform_create(self, serializer):
        if self.to_one_field_name is None:
            raise ValueError(
                'You must either set "to_one_field_name" or override this method.')

        # This makes sure that the object specified in the url
        # is the one that the newly created object belongs to,
        # even if something different is specified in the
        # request body.
        serializer.save(**{self.to_one_field_name: self.get_object()})

    def post(self, request, *args, **kwargs):
        return self.create(request, *args, **kwargs)


class ListNestedModelViewSet(ListNestedModelMixin, NestedModelViewSet):
    """
    Shortcut class for a nested model view set with list functionality.
    """
    pass


class ListCreateNestedModelViewSet(ListNestedModelMixin,
                                   CreateNestedModelViewSet,
                                   NestedModelViewSet):
    """
    Shortcut class for a nested model view set with list and create
    functionality.
    """
    pass


class RetrieveCreateNestedModelViewSet(RetrieveNestedModelMixin,
                                       CreateNestedModelViewSet,
                                       NestedModelViewSet):
    """
    Shortcut class for a nested model view set with retrieve and create
    functionality.
    """
    pass


class TransactionRetrievePatchDestroyMixin(mixins.RetrieveModelMixin,
                                           TransactionPartialUpdateMixin,
                                           TransactionDestroyMixin):
    pass


def handle_object_does_not_exist_404(func):
    def decorated_func(*args, **kwargs):
        try:
            return func(*args, **kwargs)
        except ObjectDoesNotExist:
            raise Http404

    return decorated_func


def require_body_params(*required_body_params: str):
    """
    When applied to a view, checks whether each parameter listed in
    required_body_params is present in the request body. If any of
    the parameters are missing, returns a 400 response.
    """
    def decorator(view):
        def decorated_view(request: Request, *args, **kwargs):
            missing_params = []
            for param in required_body_params:
                if param not in request.data:
                    missing_params.append(param)

            if missing_params:
                error_msg = 'Missing required body parameter(s): {}'.format(
                    ', '.join(missing_params)
                )
                return response.Response(data=error_msg, status=status.HTTP_400_BAD_REQUEST)

            return view(request, *args, **kwargs)

        return decorated_view

    return decorator


def require_query_params(*required_query_params: str):
    """
    When applied to a view, checks whether each parameter listed in
    required_query_params is present in the request query string.
    If any of the parameters are missing, returns a 400 response.
    """
    def decorator(view):
        def decorated_view(request: Request, *args, **kwargs):
            missing_params = []
            for param in required_query_params:
                if param not in request.query_params:
                    missing_params.append(param)

            if missing_params:
                error_msg = 'Missing required query parameter(s): {}'.format(
                    ', '.join(missing_params)
                )
                return response.Response(data=error_msg, status=status.HTTP_400_BAD_REQUEST)

            return view(request, *args, **kwargs)

        return decorated_view

    return decorator
