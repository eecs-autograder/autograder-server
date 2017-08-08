import enum


class FeedbackCategory(enum.Enum):
    normal = 'normal'
    ultimate_submission = 'ultimate_submission'
    past_limit_submission = 'past_limit_submission'
    staff_viewer = 'staff_viewer'
    max = 'max'
