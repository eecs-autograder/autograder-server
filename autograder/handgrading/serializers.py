import autograder.handgrading.models as handgrading_models
from autograder.rest_api.serializers.ag_model_serializer import AGModelSerializer


class HandgradingRubricSerializer(AGModelSerializer):
    ag_model_class = handgrading_models.HandgradingRubric


class CriterionSerializer(AGModelSerializer):
    ag_model_class = handgrading_models.Criterion


class AnnotationSerializer(AGModelSerializer):
    ag_model_class = handgrading_models.Annotation


class HandgradingResultSerializer(AGModelSerializer):
    ag_model_class = handgrading_models.HandgradingResult


class CriterionResultSerializer(AGModelSerializer):
    ag_model_class = handgrading_models.CriterionResult


class AppliedAnnotationSerializer(AGModelSerializer):
    ag_model_class = handgrading_models.AppliedAnnotation


class CommentSerializer(AGModelSerializer):
    ag_model_class = handgrading_models.Comment


class LocationSerializer(AGModelSerializer):
    ag_model_class = handgrading_models.Location
