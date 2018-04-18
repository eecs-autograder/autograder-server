from django.core import exceptions

from rest_framework import serializers


class AGModelSerializer(serializers.BaseSerializer):
    """
    The purpose of this base class is to push data validation down to
    the database level while making it still be possible to use django-
    rest-framework's generic views when desired.
    """
    ag_model_class = None

    def get_ag_model_manager(self):
        """
        Defaults to ag_model_class.objects if that attribute is set.
        Otherwise, raises NotImplementedError.
        """
        if self.ag_model_class is not None:
            return self.ag_model_class.objects

        raise NotImplementedError(
            "Derived classes should set ag_model_class or "
            "override this method."
        )

    def to_representation(self, obj):
        if isinstance(obj, dict):
            return obj

        return obj.to_dict()

    # Derived classes may need to override this if any sub-objects need
    # to be deserialized (for example, FeedbackConfig objects)
    def to_internal_value(self, data):
        return data

    def create(self, validated_data):
        try:
            return self.validate_and_create(validated_data)
        except exceptions.ValidationError as e:
            raise serializers.ValidationError(e.message_dict)

    def validate_and_create(self, data):
        return self.get_ag_model_manager().validate_and_create(**data)

    def update(self, instance, validated_data):
        try:
            instance.validate_and_update(**validated_data)
            return instance
        except exceptions.ValidationError as e:
            raise serializers.ValidationError(e.message_dict)

    # Since we're pushing the validation down to the database
    # level, this method should return the given data unmodified.
    def run_validation(self, initial_data):
        return initial_data
