from django.shortcuts import get_object_or_404

from rest_framework import viewsets, permissions, mixins, generics

from ..transaction_mixins import (
    TransactionCreateMixin, TransactionUpdateMixin, TransactionDestroyMixin)


class GetObjectLockOnUnsafeMixin:
    """
    This mixin for Django REST Framework view classes Provides
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

    def get_object(self):
        if self.model_manager is None:
            raise ValueError('"model_manager" must not be None.')

        queryset = self.model_manager
        if self.request.method not in permissions.SAFE_METHODS:
            queryset = queryset.select_for_update()

        obj = get_object_or_404(queryset, pk=self.kwargs[self.pk_key])
        self.check_object_permissions(self.request, obj)
        return obj


class AlwaysIsAuthenticatedMixin:
    """
    Provides a version of get_permissions() that appends
    IsAuthenticated to the view's permission classes.
    """
    def get_permissions(self):
        return [permissions.IsAuthenticated()] + super().get_permissions()


class AGModelGenericViewSet(GetObjectLockOnUnsafeMixin,
                            AlwaysIsAuthenticatedMixin,
                            viewsets.GenericViewSet):
    """
    A generic viewset that includes the mixins
    GetObjectLockOnUnsafeMixin and AlwaysIsAuthenticatedMixin.
    """
    pass


class ListCreateNestedModelView(GetObjectLockOnUnsafeMixin,
                                AlwaysIsAuthenticatedMixin,
                                mixins.ListModelMixin,
                                TransactionCreateMixin,
                                generics.GenericAPIView):
    """
    Provides 'list' and 'create' functionality for models
    that conceptually cannot exist without some foreign key
    relationship.
    For 'list' and 'create' functionality, this allows Django REST
    Framework's object-level permission checking to examine the -to-one
    (foreign) related object when querying for the -to-many (related)
    objects or creating a new related object.
    For 'create' functionality, this lets us make sure that newly
    created related objects belong to the appropriate foreign object,
    as specified by a primary key loaded from the URL.

    For example, setting foreign_key_field_name to 'course'
    and reverse_foreign_key_field_name to 'projects' would allow the following:
    A GET request to /courses/2/projects/ could return a list of Projects
    that belong to Course 2, but only if the user is staff for or enrolled
    in that Course.
    A POST request to /courses/2/projects/ would create a new Project that
    belongs to Course 2 (overriding any 'course' field included in the
    request body), but only if the user is admin for that Course.
    """

    foreign_key_field_name = None
    reverse_foreign_key_field_name = None

    def get_queryset(self):
        if self.reverse_foreign_key_field_name is None:
            raise ValueError('"reverse_foreign_key_field_name" must not be None.')

        return getattr(self.get_object(), self.reverse_foreign_key_field_name).all()

    def perform_create(self, serializer):
        if self.foreign_key_field_name is None:
            raise ValueError(
                'You must either set "foreign_key_field_name" or override this method.')

        # This makes sure that the object specified in the url
        # is the one that the newly created object belongs to,
        # even if something different is specified in the
        # request body.
        serializer.save(**{self.foreign_key_field_name: self.get_object()})

    def get(self, request, *args, **kwargs):
        return self.list(request, *args, **kwargs)

    def post(self, request, *args, **kwargs):
        return self.create(request, *args, **kwargs)


class TransactionRetrieveUpdateDestroyMixin(mixins.RetrieveModelMixin,
                                            TransactionUpdateMixin,
                                            TransactionDestroyMixin):
    pass
