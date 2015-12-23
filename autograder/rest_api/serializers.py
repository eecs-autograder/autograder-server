from rest_framework import serializers

from autograder.core.models import Course, Semester

from django.core.exceptions import ValidationError
from django.contrib.auth.models import User


class NoValidationSerializer(serializers.ModelSerializer):
    def validate(self, attrs):
        print('har har')
        return attrs

    def run_validators(self, value):
        print('hee hee')
        pass


class CourseSerializer(NoValidationSerializer):
    class Meta:
        model = Course
        fields = ('id', 'name')#, 'administrators')

    def create(self, validated_data):
        raise serializers.ValidationError({
            "name": [
                "waaaaaaluigi"
            ]
        })
        print(validated_data)
        try:
            return Course.objects.validate_and_create(**validated_data)
        except ValidationError:
            print('caught django validation error')
            raise
        except serializers.ValidationError:
            print('caught rest validation error')
            raise


# class UserSerializer(serializers.ModelSerializer):
#     class Meta:
#

class SemesterSerializer(NoValidationSerializer):
    class Meta:
        model = Semester
        fields = ('id', 'name', 'course')
