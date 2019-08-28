from drf_yasg.openapi import Parameter
from rest_framework.exceptions import ValidationError

import autograder.core.models as ag_models

FDBK_CATEGORY_PARAM = 'feedback_category'


def validate_fdbk_category(fdbk_category: str) -> ag_models.FeedbackCategory:
    try:
            return ag_models.FeedbackCategory(fdbk_category)
    except ValueError:
        raise ValidationError({
            FDBK_CATEGORY_PARAM: 'Invalid value: {}'.format(fdbk_category)
        })


def make_fdbk_category_param_docs(*, required: bool=True, in_: str='query'):
    return Parameter(
        name=FDBK_CATEGORY_PARAM,
        in_=in_,
        required=required,
        type='string',
        enum=[item.value for item in ag_models.FeedbackCategory],
        description=f"""
The category of feedback being requested. Must be one of the following
values:

    - {ag_models.FeedbackCategory.normal.value}: Can be requested by
        students before or after the project deadline on their
        submissions that did not exceed the daily limit.
    - {ag_models.FeedbackCategory.past_limit_submission.value}: Can be
        requested by students on their submissions that exceeded the
        daily limit.
    - {ag_models.FeedbackCategory.ultimate_submission.value}: Can be
        requested by students on their own ultimate (a.k.a. final
        graded) submission once the project deadline has passed and
        hide_ultimate_submission_fdbk has been set to False on the
        project. Can similarly be requested by staff when looking
        up another user's ultimate submission results after the
        deadline.
    - {ag_models.FeedbackCategory.staff_viewer.value}: Can be requested
        by staff when looking up another user's submission results.
    - {ag_models.FeedbackCategory.max.value}: Can be requested by staff
        on their own submissions."""
    )
