from django.shortcuts import get_object_or_404
from rest_framework import permissions


def build_load_object_mixin(ag_model_class, pk_key='pk'):
    """
    Returns a mixin class that provides an implementation of get_object
    that can be used in a Django Rest Framework generic viewset:
    http://www.django-rest-framework.org/api-guide/viewsets/#genericviewset

    Note: The implementation of get_object will also call
    select_for_update() on the default manager if the request method is
    not a 'safe method'.

    Note: The implementation of get_object will raise an HTTP 404 error
    if the object being looked up does not exist.

    Params:
        ag_model_class -- A class that inherits from the autograder
            model base class. This class determines the type of object
            that will be loaded.

        pk_key -- A string that will be used to look up the primary key
            of the object being loaded. The primary key will be loaded
            from the kwargs dictionary that is built from parsing the
            url. By default, this value is 'pk'.
    """
    class LoadObjectMixin:
        def load_object(self, pk):
            manager = ag_model_class.objects
            if self.request.method not in permissions.SAFE_METHODS:
                manager = manager.select_for_update()

            obj = get_object_or_404(manager, pk=pk)
            self.check_object_permissions(self.request, obj)
            return obj

        def get_object(self):
            return self.load_object(self.kwargs[pk_key])

    return LoadObjectMixin
