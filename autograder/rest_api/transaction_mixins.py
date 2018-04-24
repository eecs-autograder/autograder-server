from django.db import transaction

from rest_framework import mixins, response


class PartialUpdateMixin:
    def perform_update(self, serializer):
        serializer.save()

    # Implementation adapted from
    # https://github.com/encode/django-rest-framework/blob/master/rest_framework/mixins.py#L61
    # on 2018-04-24
    def partial_update(self, request, *args, **kwargs):
        instance = self.get_object()
        serializer = self.get_serializer(instance, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        self.perform_update(serializer)

        if getattr(instance, '_prefetched_objects_cache', None):
            # If 'prefetch_related' has been applied to a queryset, we need to
            # forcibly invalidate the prefetch cache on the instance.
            instance._prefetched_objects_cache = {}

        return response.Response(serializer.data)


class TransactionCreateMixin(mixins.CreateModelMixin):
    @transaction.atomic()
    def create(self, *args, **kwargs):
        return super().create(*args, **kwargs)


class TransactionPartialUpdateMixin(PartialUpdateMixin):
    @transaction.atomic()
    def partial_update(self, *args, **kwargs):
        return super().partial_update(*args, **kwargs)


class TransactionDestroyMixin(mixins.DestroyModelMixin):
    @transaction.atomic()
    def destroy(self, *args, **kwargs):
        return super().destroy(*args, **kwargs)
