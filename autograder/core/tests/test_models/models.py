from django.core import validators
from django.db import models

from autograder.core.models import AutograderModel

# -----------------------------------------------------------------------------
# DUMMY MODELS FOR TESTING AUTOGRADER MODEL BASE CLASS
# -----------------------------------------------------------------------------


class _DummyAutograderModel(AutograderModel):
    pos_num_val = models.IntegerField(
        validators=[validators.MinValueValidator(0)])
    non_empty_str_val = models.TextField(
        validators=[validators.MinLengthValidator(1)])

    @property
    def the_answer(self):
        return 42

    _DEFAULT_TO_DICT_FIELDS = frozenset([
        'pos_num_val',
        'non_empty_str_val',
        'the_answer',
    ])

    @classmethod
    def get_default_to_dict_fields(class_):
        return class_._DEFAULT_TO_DICT_FIELDS


class _DummyForeignAutograderModel(AutograderModel):
    name = models.CharField(max_length=255)
    one_to_one = models.OneToOneField(_DummyAutograderModel)
    foreign_key = models.ForeignKey(_DummyAutograderModel,
                                    related_name='dummies')
    nullable_one_to_one = models.OneToOneField(
        _DummyAutograderModel,
        blank=True, null=True, default=None,
        related_name='nullables')

    _DEFAULT_TO_DICT_FIELDS = frozenset([
        'name',
        'one_to_one',
        'foreign_key',
        'nullable_one_to_one'
    ])

    @classmethod
    def get_default_to_dict_fields(class_):
        return class_._DEFAULT_TO_DICT_FIELDS
