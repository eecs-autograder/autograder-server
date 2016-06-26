from django.shortcuts import get_object_or_404
from rest_framework import permissions


def build_load_object_mixin(ag_model_class):
    class LoadObjectMixin:
        def load_object(self, pk):
            manager = ag_model_class.objects
            if self.request.method not in permissions.SAFE_METHODS:
                manager = manager.select_for_update()

            course = get_object_or_404(manager, pk=pk)
            self.check_object_permissions(self.request, course)
            return course

    return LoadObjectMixin
