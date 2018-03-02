import autograder.handgrading.models as handgrading_models
from autograder.rest_api.serializers.ag_model_serializer import AGModelSerializer


class HandgradingRubricSerializer(AGModelSerializer):
    def get_ag_model_manager(self):
        return handgrading_models.HandgradingRubric.objects


class CriterionSerializer(AGModelSerializer):
    def get_ag_model_manager(self):
        return handgrading_models.Criterion.objects


class AnnotationSerializer(AGModelSerializer):
    def get_ag_model_manager(self):
        return handgrading_models.Annotation.objects


class HandgradingResultSerializer(AGModelSerializer):
    def get_ag_model_manager(self):
        return handgrading_models.HandgradingResult.objects


class CriterionResultSerializer(AGModelSerializer):
    def get_ag_model_manager(self):
        return handgrading_models.CriterionResult.objects


class AppliedAnnotationSerializer(AGModelSerializer):
    def get_ag_model_manager(self):
        return handgrading_models.AppliedAnnotation.objects


class CommentSerializer(AGModelSerializer):
    def get_ag_model_manager(self):
        return handgrading_models.Comment.objects


class LocationSerializer(AGModelSerializer):
    def get_ag_model_manager(self):
        return handgrading_models.Location.objects
