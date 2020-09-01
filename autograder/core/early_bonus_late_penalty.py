from datetime import timedelta

import autograder.core.models as ag_models


def compute_early_submission_bonus_percent(submission: ag_models.Submission) -> int:
    """
    Returns the percentage early submission bonus to apply.
    """
    if not submission.project.use_early_submission_bonus:
        return 0

    project = submission.project
    group = submission.group

    deadline = None
    if project.early_submission_bonus.use_hard_deadline:
        if group.extended_due_date is not None:
            deadline = group.extended_due_date
        else:
            deadline = project.closing_time
    else:
        if group.soft_extended_due_date is not None:
            deadline = group.soft_extended_due_date
        else:
            deadline = project.soft_closing_time

    if submission.timestamp >= deadline:
        return 0

    amount_early = deadline - submission.timestamp
    multiplier = amount_early // timedelta(hours=project.early_submission_bonus.per_num_hours)

    return min(
        project.early_submission_bonus.percent_bonus * multiplier,
        project.early_submission_bonus.max_percent_bonus
    )


def compute_late_submission_penalty_percent(submission: ag_models.Submission) -> int:
    """
    Returns the percentage late submission penalty to apply.
    """
    if not submission.project.use_late_submission_penalty:
        return 0

    project = submission.project
    group = submission.group

    deadline = None
    if group.soft_extended_due_date is not None:
        deadline = group.soft_extended_due_date
    else:
        deadline = project.soft_closing_time

    if submission.timestamp <= deadline:
        return 0

    amount_late = submission.timestamp - deadline
    multiplier = amount_late // timedelta(hours=project.late_submission_penalty.per_num_hours)
    remainder = amount_late % timedelta(hours=project.late_submission_penalty.per_num_hours)
    if remainder:
        multiplier += 1

    return min(
        project.late_submission_penalty.percent_penalty * multiplier,
        project.late_submission_penalty.max_percent_penalty
    )

    # # WHERE SHOULD THIS GO????
    # # We need it for:
    # # - getting ultimate fdbk for one submission
    # # - getting ultimate fdbk for ultimate submissions for all groups
    # #   (API requests and spreadsheets)
    # def _adjust_score_for_early_bonus_or_late_penalty(
    #     self,
    #     submission_fdbk: SubmissionResultFeedback,
    # ) -> Dict[str, object]:
    #     if submission_fdbk.fdbk_category != ag_models.FeedbackCategory.ultimate_submission:
    #         return submission_fdbk.to_dict()

    #     early_bonus_percent = 0
    #     late_penalty_percent = 0

    #     project = submission_fdbk.project

    #     if project.use_early_submission_bonus:
    #         early_bonus_percent = self._compute_early_submission_bonus(project, fdbk_dict)

    #     if project.use_late_submission_penalty:
    #         late_penalty_percent = self._compute_late_submission_penalty(project, fdbk, dict)

    #     subtotal = submission_fdbk.total_points
    #     fdbk_dict = submission_fdbk.to_dict()

    #     if early_bonus_percent != 0:
    #         # fdbk_dict['subtotal'] = subtotal
    #         # fdbk_dict['total_points'] *= 1 + early_bonus_percent / 100
    #         pass
    #     elif late_penalty_percent != 0:
    #         pass



