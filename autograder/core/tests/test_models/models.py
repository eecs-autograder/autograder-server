from django.core import validators
from django.db import models
from django.contrib.auth.models import User

from autograder.core.models import AutograderModel

# -----------------------------------------------------------------------------
# DUMMY MODELS FOR TESTING AutograderModel BASE CLASS
# -----------------------------------------------------------------------------


class _DummyToManyModel(AutograderModel):
    class Meta:
        ordering = ('name',)

    name = models.CharField(max_length=255)

    SERIALIZABLE_FIELDS = ('name',)
    EDITABLE_FIELDS = ('name',)


class _DummyForeignAutograderModel(AutograderModel):
    name = models.CharField(max_length=255)

    SERIALIZABLE_FIELDS = ('name', 'rev_foreign_key')
    EDITABLE_FIELDS = ('name',)


def _make_default_dummy_foreign_ag_model():
    return _DummyForeignAutograderModel.objects.create().pk


class _DummyAutograderModel(AutograderModel):
    pos_num_val = models.IntegerField(
        validators=[validators.MinValueValidator(0)])
    non_empty_str_val = models.TextField(
        validators=[validators.MinLengthValidator(1)])
    read_only_field = models.TextField(blank=True)

    one_to_one = models.OneToOneField(_DummyForeignAutograderModel, related_name='rev_one_to_one')
    nullable_one_to_one = models.OneToOneField(
        _DummyForeignAutograderModel, related_name='+', blank=True, null=True, default=None)
    transparent_to_one = models.OneToOneField(
        _DummyForeignAutograderModel, related_name='+',
        default=_make_default_dummy_foreign_ag_model)

    foreign_key = models.ForeignKey(_DummyForeignAutograderModel, related_name='rev_foreign_key')
    nullable_foreign_key = models.ForeignKey(
        _DummyForeignAutograderModel, related_name='+', blank=True, null=True, default=None)
    transparent_foreign_key = models.OneToOneField(
        _DummyForeignAutograderModel, related_name='+',
        default=_make_default_dummy_foreign_ag_model)

    many_to_many = models.ManyToManyField(_DummyToManyModel, related_name='many_to_manys')
    another_many_to_many = models.ManyToManyField(_DummyToManyModel)

    users = models.ManyToManyField(User)

    @property
    def the_answer(self):
        return 42

    SERIALIZABLE_FIELDS = (
        'pos_num_val',
        'non_empty_str_val',
        'the_answer',

        'one_to_one',
        'nullable_one_to_one',
        'transparent_to_one',

        'foreign_key',
        'nullable_foreign_key',
        'transparent_foreign_key',

        'many_to_many',
        'another_many_to_many',

        'users'
    )

    EDITABLE_FIELDS = (
        'pos_num_val',
        'non_empty_str_val',

        'one_to_one',
        'nullable_one_to_one',
        'transparent_to_one',

        'foreign_key',
        'nullable_foreign_key',
        'transparent_foreign_key',

        'many_to_many',
        'another_many_to_many',

        'users'
    )

    TRANSPARENT_TO_ONE_FIELDS = (
        'transparent_to_one',
        'transparent_foreign_key'
    )
