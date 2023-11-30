from abc import abstractmethod
from functools import wraps
from typing import Any, Callable, Dict, List, Optional, Protocol, TypeVar, Union, cast

from django.core.exceptions import ObjectDoesNotExist
from django.core.exceptions import ValidationError as DjangoValidationError
from django.db import transaction
from django.http import Http404
from django.shortcuts import get_object_or_404
from rest_framework import mixins, permissions, response, status, viewsets
from rest_framework.exceptions import ValidationError as DRFValidationError
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView


# See https://github.com/python/mypy/issues/3157
_DecoratedFunc = TypeVar('_DecoratedFunc', bound=Callable[..., Any])


def convert_django_validation_error(func: _DecoratedFunc) -> _DecoratedFunc:
    """
    If the decorated function raises django.core.exceptions.ValidationError,
    catches the error and raises rest_framework.exceptions.ValidationError
    with the same content.
    """
    @wraps(func)
    def decorated_func(*args, **kwargs):  # type: ignore  ## Wait for PEP 612
        try:
            return func(*args, **kwargs)
        except DjangoValidationError as e:
            detail: Union[str, List[Any], Dict[str, Any]] = ''
            if hasattr(e, 'message_dict'):
                detail = e.message_dict
            elif hasattr(e, 'message'):
                detail = e.message
            elif hasattr(e, 'messages'):
                detail = e.messages

            raise DRFValidationError(detail)

    return cast(_DecoratedFunc, decorated_func)


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


class AGModelDetailView(AGModelAPIView):
    """
    A view base class used for defining endpoints that operate on a
    single object, e.g. retrieving, updating, deleting.
    """
    def do_get(self):
        return response.Response(self.serialize_object(self.get_object()))

    @convert_django_validation_error
    @transaction.atomic
    def do_patch(self):
        obj = self.get_object()
        obj.validate_and_update(**self.request.data)
        return response.Response(data=self.serialize_object(obj), status=status.HTTP_200_OK)

    @transaction.atomic
    def do_delete(self):
        self.get_object().delete()
        return response.Response(status=status.HTTP_204_NO_CONTENT)

    def serialize_object(self, obj):
        return obj.to_dict()


class NestedModelView(AGModelAPIView):
    """
    A view base class used for defining endpoints that operate on collections
    of objects that belong to one model type, e.g. Projects for a Course.
    """
    def get_nested_manager(self):
        """
        Returns a model manager of objects related to the one loaded with
        self.get_object().
        """
        if self.nested_field_name is None:
            raise ValueError('"nested_field_name" must not be None.')

        return getattr(self.get_object(), self.nested_field_name)

    # The name of the relationship that can be used to load the nested objects.
    # For example, if loading Projects from a Course, this attribute would
    # have the value 'projects'.
    # If NestedModelView.get_nested_manager(), NestedModelView.do_retrieve(),
    # or NestedModelView.do_list() are
    # to be called, this attribute must be non-null.
    nested_field_name: Optional[str] = None

    # In the object being created, the name of the field whose
    # value is the parent object (the object loaded with self.get_object()).
    # For example, if creating a new Project for a Course, this attribute
    # would have the value 'course'.
    # If NestedModelView.do_create() is to be called,
    # this attribute must be non-null.
    parent_obj_field_name: Optional[str] = None

    def do_list(self):
        return Response(
            data=[self.serialize_object(obj) for obj in self.get_nested_manager().all()],
            status=status.HTTP_200_OK,
        )

    @convert_django_validation_error
    @transaction.atomic
    def do_create(self):
        data = dict(self.request.data)
        data[self.parent_obj_field_name] = self.get_object()

        queryset = self.get_nested_manager()
        result = queryset.validate_and_create(**data)
        return Response(
            data=self.serialize_object(result),
            status=status.HTTP_201_CREATED
        )

    def serialize_object(self, obj):
        return obj.to_dict()


def handle_object_does_not_exist_404(func):
    @wraps(func)
    def decorated_func(*args, **kwargs):
        try:
            return func(*args, **kwargs)
        except ObjectDoesNotExist:
            raise Http404

    return decorated_func


def require_body_params(*required_body_params: str):
    """
    When applied to a DRF view, checks whether each parameter listed in
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


def require_non_null_body_params(*non_null_body_params: str):
    """
    When applied to a DRF view, checks whether each parameter listed in
    non_null_body_params is not None *if present* in the request body.
    Missing parameters are skipped.
    If any of the specifieg parameters are present and None,
    returns a 400 response.
    """
    def decorator(view):
        def decorated_view(request: Request, *args, **kwargs):
            null_params = []
            for param in non_null_body_params:
                if param in request.data and request.data[param] is None:
                    null_params.append(param)

            if null_params:
                error_msg = 'These body parameter(s) must not be null: {}'.format(
                    ', '.join(null_params)
                )
                return response.Response(data=error_msg, status=status.HTTP_400_BAD_REQUEST)

            return view(request, *args, **kwargs)

        return decorated_view

    return decorator


def require_query_params(*required_query_params: str):
    """
    When applied to a DRF view, checks whether each parameter listed in
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
