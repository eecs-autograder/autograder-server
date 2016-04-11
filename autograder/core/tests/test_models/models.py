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

    DEFAULT_INCLUDE_FIELDS = frozenset([
        'pos_num_val',
        'non_empty_str_val',
        'the_answer',
    ])


class _DummyForeignAutograderModel(AutograderModel):
    name = models.CharField(max_length=255)
    one_to_one = models.OneToOneField(_DummyAutograderModel)

    DEFAULT_INCLUDE_FIELDS = frozenset([
        'name',
        'one_to_one'
    ])
