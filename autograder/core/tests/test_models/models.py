import enum

from django.core import validators
from django.db import models
from django.contrib.auth.models import User

from autograder.core.models import AutograderModel
import autograder.core.fields as ag_fields
from autograder.core.models.ag_model_base import DictSerializableMixin

# -----------------------------------------------------------------------------
# DUMMY MODELS FOR TESTING AutograderModel BASE CLASS
# -----------------------------------------------------------------------------


class DummyToManyModel(AutograderModel):
    class Meta:
        ordering = ('name',)

    name = models.CharField(max_length=255)

    SERIALIZABLE_FIELDS = ('pk', 'name',)
    EDITABLE_FIELDS = ('name',)


class DummyForeignAutograderModel(AutograderModel):
    name = models.CharField(max_length=255)

    SERIALIZABLE_FIELDS = ('pk', 'name', 'rev_foreign_key')
    EDITABLE_FIELDS = ('name',)


def _make_default_dummy_foreign_ag_model():
    return DummyForeignAutograderModel.objects.create().pk


class AnEnum(enum.Enum):
    spam = 'spam'
    egg = 'egg'


class DummyAutograderModel(AutograderModel):
    pos_num_val = models.IntegerField(
        validators=[validators.MinValueValidator(0)])
    non_empty_str_val = models.TextField(
        validators=[validators.MinLengthValidator(1)])
    read_only_field = models.TextField(blank=True)

    enum_field = ag_fields.EnumField(AnEnum, blank=True, default=AnEnum.spam)

    one_to_one = models.OneToOneField(DummyForeignAutograderModel, related_name='rev_one_to_one',
                                      on_delete=models.CASCADE)
    nullable_one_to_one = models.OneToOneField(
        DummyForeignAutograderModel, related_name='+', blank=True, null=True, default=None,
        on_delete=models.SET_NULL)

    foreign_key = models.ForeignKey(DummyForeignAutograderModel, related_name='rev_foreign_key',
                                    on_delete=models.CASCADE)
    nullable_foreign_key = models.ForeignKey(
        DummyForeignAutograderModel, related_name='+', blank=True, null=True, default=None,
        on_delete=models.CASCADE)

    many_to_many = models.ManyToManyField(DummyToManyModel, related_name='many_to_manys')
    another_many_to_many = models.ManyToManyField(DummyToManyModel)

    users = models.ManyToManyField(User)

    @property
    def the_answer(self):
        return 42

    @property
    def enum_property(self):
        return AnEnum.egg

    SERIALIZABLE_FIELDS = (
        'pk',
        'pos_num_val',
        'non_empty_str_val',
        'the_answer',
        'enum_property',

        'enum_field',

        'one_to_one',
        'one_to_one_id',
        'nullable_one_to_one',
        'nullable_one_to_one_id',

        'foreign_key',
        'foreign_key_id',
        'nullable_foreign_key',
        'nullable_foreign_key_id',

        'many_to_many',
        'another_many_to_many',

        'users'
    )

    EDITABLE_FIELDS = (
        'pos_num_val',
        'non_empty_str_val',

        'enum_field',

        'one_to_one',
        'nullable_one_to_one',

        'foreign_key',
        'nullable_foreign_key',

        'many_to_many',
        'another_many_to_many',

        'users'
    )


class DictSerializableClass(DictSerializableMixin):
    has_default_default_val = 8769

    def __init__(self, num: int, string: str, an_enum: AnEnum,
                 has_default: int=has_default_default_val):
        self.num = num
        self.string = string
        self.an_enum = an_enum
        self.has_default = has_default

    SERIALIZABLE_FIELDS = [
        'num',
        'string',
        'an_enum',
        'has_default'
    ]


class AGModelWithSerializableField(AutograderModel):
    serializable = ag_fields.ValidatedJSONField(DictSerializableClass)
    nullable_serializable = ag_fields.ValidatedJSONField(
        DictSerializableClass, blank=True, null=True, default=None)

    SERIALIZABLE_FIELDS = ('serializable', 'nullable_serializable',)
    EDITABLE_FIELDS = ('serializable', 'nullable_serializable',)


class AGModelWithDecimalField(AutograderModel):
    decimal_field = models.DecimalField(max_digits=3, decimal_places=2)

    SERIALIZABLE_FIELDS = ['decimal_field']
