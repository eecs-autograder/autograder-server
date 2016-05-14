from rest_framework import serializers
from django.core import exceptions


class AGModelSerializer(serializers.BaseSerializer):
    """
    The purpose of this base class is to push data validation down to
    the database level while making it still be possible to use django-
    rest-framework's generic views when desired.
    """

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.include_fields = None
        self.exclude_fields = None

        if not self.context:
            return

        self.include_fields = (
            self.context['request'].query_params.getall('include_fields'))
        self.exclude_fields = (
            self.context['request'].query_params.getall('exclude_fields'))

    def get_ag_model_manager(self):
        """
        Returns a django model manager object that can be used to create
        objects of the desired autograder model type.
        """
        raise NotImplementedError(
            "Derived classes must override this method")

    def to_representation(self, obj):
        return obj.to_dict(include_fields=self.include_fields,
                           exclude_fields=self.exclude_fields)

    # Subclasses may need to override this if any sub-objects need to be
    # deserialized (for example, FeedbackConfig objects)
    def to_internal_value(self, data):
        return data

    def create(self, validated_data):
        try:
            return self.get_ag_model_manager().validate_and_create(
                **validated_data)
        except exceptions.ValidationError as e:
            raise serializers.ValidationError(e.message_dict)

    def update(self, instance, validated_data):
        try:
            instance.validate_and_update(**validated_data)
            return instance
        except exceptions.ValidationError as e:
            raise serializers.ValidationError(e.message_dict)

    # Since we're pushing the validation down to the database
    # level, this method should do nothing.
    def run_validation(self, initial_data):
        return initial_data
