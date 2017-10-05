"""
The following create models for handgrading using default values for testing.
"""

import copy

import autograder.utils.testing.model_obj_builders as obj_build
import autograder.handgrading.models as handgrading_models

def create_handgrading_rubric(rubric_kwargs: dict = None,
                              project_kwargs: dict = None) -> handgrading_models.HandgradingRubric:
    """
    Creates and returns a HandgradingRubric object
    Any fields in rubric_kwargs will be used instead of defaults.

    If the dictionary "project_kwargs" is included, the handgrading rubric's Project primary key
    will be created using its values.
    """

    if rubric_kwargs is None:
        rubric_kwargs_in = {}
    else:
        rubric_kwargs_in = copy.deepcopy(rubric_kwargs)

    if 'project' not in rubric_kwargs_in:
        rubric_kwargs_in['project'] = obj_build.build_project()
    elif project_kwargs != None:
        rubric_kwargs_in['project'] = obj_build.build_project(project_kwargs=project_kwargs)

    if 'points_style' not in rubric_kwargs_in:
        rubric_kwargs_in['points_style'] = handgrading_models.PointsStyle.start_at_zero_and_add

    if 'max_points' not in rubric_kwargs_in:
        rubric_kwargs_in['max_points'] = 10

    if 'show_grades_and_rubric_to_students' not in rubric_kwargs_in:
        rubric_kwargs_in['show_grades_and_rubric_to_students'] = True

    if 'handgraders_can_leave_comments' not in rubric_kwargs_in:
        rubric_kwargs_in['handgraders_can_leave_comments'] = True

    if 'handgraders_can_apply_arbitrary_points' not in rubric_kwargs_in:
        rubric_kwargs_in['handgraders_can_apply_arbitrary_points'] = True

    handgrading_rubric = handgrading_models.HandgradingRubric.objects.validate_and_create(
        **rubric_kwargs_in)
    return handgrading_rubric


def create_criterion(criterion_kwargs: dict = None,
                     rubric_kwargs: dict = None) -> handgrading_models.Criterion:
    """
    Creates and returns a Criterion object
    Any fields in criterion_kwargs will be used instead of defaults.

    If the dictionary "rubric_kwargs" is included, the criterion's HandgradingRubric primary key
    will be created using its values.
    """

    if criterion_kwargs is None:
        criterion_kwargs_in = {}
    else:
        criterion_kwargs_in = copy.deepcopy(criterion_kwargs)

    if 'handgrading_rubric' not in criterion_kwargs_in:
        criterion_kwargs_in['handgrading_rubric'] = create_handgrading_rubric()
    elif rubric_kwargs is not None:
        criterion_kwargs_in['handgrading_rubric'] = create_handgrading_rubric(
            rubric_kwargs=rubric_kwargs)

    if 'short_description' not in criterion_kwargs_in:
        criterion_kwargs_in['short_description'] = "Testing short description"

    if 'long_description' not in criterion_kwargs_in:
        criterion_kwargs_in['long_description'] = "Testing long description. This should be long."

    if 'points' not in criterion_kwargs_in:
        criterion_kwargs_in['points'] = 25

    criterion = handgrading_models.Criterion.objects.validate_and_create(**criterion_kwargs_in)
    return criterion


def create_annotation(annotation_kwargs: dict = None,
                      rubric_kwargs: dict = None) -> handgrading_models.Annotation:
    """
    Creates and returns a Annotation object
    Any fields in annotation_kwargs will be used instead of defaults.

    If the dictionary "rubric_kwargs" is included, the annotation's HandgradingRubric primary key
    will be created using its values.
    """

    if annotation_kwargs is None:
        annotation_kwargs_in = {}
    else:
        annotation_kwargs_in = copy.deepcopy(annotation_kwargs)

    if 'handgrading_rubric' not in annotation_kwargs_in:
        annotation_kwargs_in['handgrading_rubric'] = create_handgrading_rubric()
    elif rubric_kwargs is not None:
        annotation_kwargs_in['handgrading_rubric'] = \
            create_handgrading_rubric(rubric_kwargs=rubric_kwargs)

    if 'short_description' not in annotation_kwargs_in:
        annotation_kwargs_in['short_description'] = "Testing short description"

    if 'long_description' not in annotation_kwargs_in:
        annotation_kwargs_in['long_description'] = "Testing long description. This should be long."

    if 'points' not in annotation_kwargs_in:
        annotation_kwargs_in['points'] = 25

    annotation = handgrading_models.Annotation.objects.validate_and_create(**annotation_kwargs_in)
    return annotation


def create_applied_annotation(app_annotation_kwargs: dict = None,
                              result_kwargs: dict = None,
                              annotation_kwargs: dict = None,
                              location_kwargs: dict = None) -> handgrading_models.AppliedAnnotation:
    """
    Creates and returns a Applied Annotation object
    Any fields in app_annotation_kwargs will be used instead of defaults specified below.

    If the dictionary "result_kwargs" is included, the applied annotation's HandgradingResult
    primary key will be created using its values.

    If the dictionary "annotation_kwargs" is included, the applied annotation's Annotation
    primary key will be created using its values.
    """

    if app_annotation_kwargs is None:
        app_annotation_kwargs_in = {}
    else:
        app_annotation_kwargs_in = copy.deepcopy(app_annotation_kwargs)

    if 'handgrading_result' not in app_annotation_kwargs_in:
        app_annotation_kwargs_in['handgrading_result'] = create_handgrading_result()
    elif result_kwargs is not None:
        app_annotation_kwargs_in['handgrading_result'] = create_handgrading_result(
            result_kwargs=result_kwargs)

    if 'location' not in app_annotation_kwargs_in:
        app_annotation_kwargs_in['location'] = create_location()
    elif location_kwargs is not None:
        app_annotation_kwargs_in['location'] = create_location(location_kwargs=location_kwargs)

    if 'annotation' not in app_annotation_kwargs_in:
        app_annotation_kwargs_in['annotation'] = create_annotation()
    elif annotation_kwargs is not None:
        app_annotation_kwargs_in['annotation'] = create_annotation(annotation_kwargs=annotation_kwargs)

    if 'comment' not in app_annotation_kwargs_in:
        app_annotation_kwargs_in['comment'] = "Testing comment field."

    applied_annotation = handgrading_models.AppliedAnnotation.objects.validate_and_create(
        **app_annotation_kwargs_in)
    return applied_annotation


def create_handgrading_result(result_kwargs: dict = None,
                              submission_kwargs: dict = None) -> handgrading_models.Annotation:
    """
    Creates and returns a Handgrading Result object
    Any fields in result_kwargs will be used instead of defaults specified below.

    If the dictionary "submission_kwargs" is included, the handgrading result's Submission
    primary key will be created using its values.
    """

    if result_kwargs is None:
        result_kwargs_in = {}
    else:
        result_kwargs_in = copy.deepcopy(result_kwargs)

    if 'submission' not in result_kwargs_in:
        kwargs={"submitted_filenames": ["test.cpp"]}
        result_kwargs_in['submission'] = obj_build.build_submission(**kwargs)
    elif submission_kwargs is not None:
        result_kwargs_in['submission'] = obj_build.build_submission(**submission_kwargs)

    result_obj = handgrading_models.HandgradingResult.objects.validate_and_create(
        **result_kwargs_in)

    return result_obj


def create_comment(comment_kwargs: dict = None,
                   location_kwargs: dict = None,
                   result_kwargs: dict = None) -> handgrading_models.Comment:
    """
    Creates and returns a Comment object
    Any fields in comment_kwargs will be used instead of defaults specified below.

    If the dictionary "location_kwargs" is included, the comment's Location
    one-to-one field will be created using its values.

    If the dictionary "handgrading_result" is included, the comment's Handgrading Result
    primary key will be created using its values.
    """

    if comment_kwargs is None:
        comment_kwargs_in = {}
    else:
        comment_kwargs_in = copy.deepcopy(comment_kwargs)

    if 'location' not in comment_kwargs_in:
        comment_kwargs_in['location'] = create_location()
    elif location_kwargs is not None:
        comment_kwargs_in['location'] = create_location(**location_kwargs)

    if 'handgrading_result' not in comment_kwargs_in:
        comment_kwargs_in['handgrading_result'] = create_handgrading_result()
    elif result_kwargs is not None:
        comment_kwargs_in['handgrading_result'] = create_handgrading_result(**result_kwargs)

    if 'text' not in comment_kwargs_in:
        comment_kwargs_in['text'] = "This is sample text meant to populate a field."

    comment_obj = handgrading_models.Comment.objects.validate_and_create(
        **comment_kwargs_in)

    return comment_obj


def create_arbitrary_points(arb_points_kwargs: dict = None,
                            location_kwargs: dict = None,
                            result_kwargs: dict = None) -> handgrading_models.Comment:
    """
    Creates and returns a Arbitrary Points object
    Any fields in arb_points_kwargs will be used instead of defaults specified below.

    If the dictionary "location_kwargs" is included, the arbitrary point's Location
    one-to-one field will be created using its values.

    If the dictionary "result_kwargs" is included, the arbitrary point's Handgrading Result
    primary key will be created using its values.
    """

    if arb_points_kwargs is None:
        arb_points_kwargs_in = {}
    else:
        arb_points_kwargs_in = copy.deepcopy(arb_points_kwargs)

    if 'location' not in arb_points_kwargs_in:
        arb_points_kwargs_in['location'] = create_location()
    elif location_kwargs is not None:
        arb_points_kwargs_in['location'] = create_location(**location_kwargs)

    if 'handgrading_result' not in arb_points_kwargs_in:
        arb_points_kwargs_in['handgrading_result'] = create_handgrading_result()
    elif result_kwargs is not None:
        arb_points_kwargs_in['handgrading_result'] = create_handgrading_result(result_kwargs=result_kwargs)

    if 'points' not in arb_points_kwargs_in:
        arb_points_kwargs_in['points'] = 25

    if 'text' not in arb_points_kwargs_in:
        arb_points_kwargs_in['text'] = "This is sample text meant to populate a field."

    arb_points_obj = handgrading_models.ArbitraryPoints.objects.validate_and_create(
        **arb_points_kwargs_in)

    return arb_points_obj


def create_location(location_kwargs: dict = None) -> handgrading_models.Location:
    """
    Creates and returns a Location object
    Any fields in location_kwargs will be used instead of defaults specified below.
    """

    if location_kwargs is None:
        location_kwargs_in = {}
    else:
        location_kwargs_in = copy.deepcopy(location_kwargs)

    if 'first_line' not in location_kwargs_in:
        location_kwargs_in['first_line'] = 25

    if 'last_line' not in location_kwargs_in:
        location_kwargs_in['last_line'] = 30

    if 'file_name' not in location_kwargs_in:
        location_kwargs_in['file_name'] = "test.cpp"

    location_obj = handgrading_models.Location.objects.validate_and_create(
        **location_kwargs_in)

    return location_obj
