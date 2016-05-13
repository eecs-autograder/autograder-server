from rest_framework import serializers


class AGModelSerializer(serializers.BaseSerializer):
    """
    The purpose of this base class is to push data validation down to
    the database level while making it still be possible to use django-
    rest-framework's generic views when desired.
    """

    def get_ag_model_manager(self):
        """
        Returns a django model manager object that can be used to create
        objects of the desired autograder model type.
        """
        raise NotImplementedError(
            "Derived classes must override this method")

    def to_representation(self, obj):
        return obj.to_dict()

    # Subclasses may need to override this if any sub-objects need to be
    # deserialized (for example, FeedbackConfig objects)
    def to_internal_value(self, data):
        return data

    def create(self, validated_data):
        return self.get_ag_model_manager().validate_and_create(
            **validated_data)

    def update(self, instance, validated_data):
        instance.validate_and_update(**validated_data)
        return instance

    # Since we're pushing the validation down to the database
    # level, this method should do nothing.
    def run_validation(self, initial_data):
        return initial_data
