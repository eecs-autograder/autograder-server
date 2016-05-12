from rest_framework import serializers


class AGModelSerializer(serializers.Serializer):
    def to_representation(self, obj):
        pass

    def to_internal_value(self, data):
        pass
