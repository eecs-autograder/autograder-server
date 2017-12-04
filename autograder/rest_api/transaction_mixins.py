from django.db import transaction

from rest_framework import mixins


class TransactionCreateMixin(mixins.CreateModelMixin):
    @transaction.atomic()
    def create(self, *args, **kwargs):
        return super().create(*args, **kwargs)


class TransactionUpdateMixin(mixins.UpdateModelMixin):
    @transaction.atomic()
    def update(self, *args, **kwargs):
        return super().update(*args, **kwargs)

    @transaction.atomic()
    def partial_update(self, *args, **kwargs):
        return super().partial_update(*args, **kwargs)


class TransactionDestroyMixin(mixins.DestroyModelMixin):
    @transaction.atomic()
    def destroy(self, *args, **kwargs):
        return super().destroy(*args, **kwargs)


class TransactionRetrieveMixin(mixins.RetrieveModelMixin):
    @transaction.atomic()
    def retrieve(self, *args, **kwargs):
        return super().retrieve(*args, **kwargs)
