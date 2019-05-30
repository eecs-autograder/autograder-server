import autograder.core.models as ag_models
import autograder.handgrading.models as hg_models


def import_handgrading_rubric(*, import_to: ag_models.Project, import_from: ag_models.Project):
    """
    Replaces import_to's handgrading rubric with a copy of import_from's
    rubric. This includes Criteria, Annotations, etc. but no results.
    """
    if hasattr(import_to, 'handgrading_rubric'):
        import_to.handgrading_rubric.delete()

    new_rubric = hg_models.HandgradingRubric.objects.get(pk=import_from.handgrading_rubric.pk)
    new_rubric.pk = None
    new_rubric.project = import_to
    new_rubric.show_grades_and_rubric_to_students = False
    new_rubric.save()

    for criterion in import_from.handgrading_rubric.criteria.all():
        criterion.pk = None
        criterion.handgrading_rubric = new_rubric
        criterion.save()

    for annotation in import_from.handgrading_rubric.annotations.all():
        annotation.pk = None
        annotation.handgrading_rubric = new_rubric
        annotation.save()
