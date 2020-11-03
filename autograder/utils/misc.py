import os
from decimal import Decimal
from typing import Callable, Iterable, Optional, Sequence, TypeVar

from django.contrib import auth


def count_if(iterable, unary_predicate):
    """
    Returns the number of items in iterable for which unary_predicate
    returns True.
    """
    return sum(1 for item in iterable if unary_predicate(item))


_T = TypeVar('_T')


def find_if(iterable: Iterable[_T], unary_predicate: Callable[[_T], bool]) -> Optional[_T]:
    """
    Returns the first element for which unary_predicate returns True.
    Returns None if no such element could be found.
    """
    return next((item for item in iterable if unary_predicate(item)), None)


def lock_users(users_iterable):
    """
    Calls select_for_update() on a queryset that includes all the users
    in users_iterable.
    """
    # list() forces the queryset to be evaluated)
    queryset = auth.models.User.objects.select_for_update().filter(
        pk__in=(user.pk for user in users_iterable))
    list(queryset)


def exclude_dict(dict_: dict, exclude_fields: Sequence[str]):
    return {key: value for key, value in dict_.items() if key not in exclude_fields}


def filter_dict(dict_: dict, include_fields: Sequence[str]):
    return {key: value for key, value in dict_.items() if key in include_fields}


class ChangeDirectory:
    """
    Enables moving into and out of a given directory using "with" statements.
    """

    def __init__(self, new_dir):
        self._original_dir = os.getcwd()
        self._new_dir = new_dir

    def __enter__(self):
        os.chdir(self._new_dir)

    def __exit__(self, *args):
        os.chdir(self._original_dir)


def two_decimal_place_string(dec: Decimal) -> str:
    return str(dec.quantize(Decimal('.01')))
