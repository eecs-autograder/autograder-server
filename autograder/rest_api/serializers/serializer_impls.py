import copy

import autograder.core.models as ag_models

from .ag_model_serializer import AGModelSerializer


class CourseSerializer(AGModelSerializer):
    def get_ag_model_manager(self):
        return ag_models.Course.objects


class ProjectSerializer(AGModelSerializer):
    def get_ag_model_manager(self):
        return ag_models.Project.objects


class UploadedFileSerializer(AGModelSerializer):
    def get_ag_model_manager(self):
        return ag_models.UploadedFile.objects


class ExpectedStudentFilePatternSerializer(AGModelSerializer):
    def get_ag_model_manager(self):
        return ag_models.ExpectedStudentFilePattern.objects


class AGTestCaseSerializer(AGModelSerializer):
    def __init__(self, *args, **kwargs):
        if 'data' not in kwargs:
            return super().__init__(*args, **kwargs)

        data = copy.copy(kwargs.pop('data'))
        for fdbk_field in ag_models.AutograderTestCaseBase.FBDK_FIELD_NAMES:
            if fdbk_field in data:
                data[fdbk_field] = (
                    ag_models.FeedbackConfig.objects.validate_and_create(
                        **data[fdbk_field]))

        return super().__init__(*args, data=data, **kwargs)

    def validate_and_create(self, data):
        return ag_models.AutograderTestCaseFactory.validate_and_create(**data)


class AGTestResultSerializer(AGModelSerializer):
    def save(self, *args, **kwargs):
        raise NotImplementedError(
            'Creating or updating AG test results is not supported')

    def create(self, validated_data):
        raise NotImplementedError('Updating AG test results is not supported')

    def update(self, instance, validated_data):
        raise NotImplementedError('Creating AG test results is not supported')

    def to_representation(self, obj):
        if not self.context:
            obj = obj.get_feedback()
            return super().to_representation(obj)

        request = self.context['request']
        student_view = request.query_params.get('student_view', False)
        obj = obj.get_feedback(user_requesting_data=request.user,
                               student_view=student_view)
        return super().to_representation(obj)


class SubmissionGroupSerializer(AGModelSerializer):
    def get_ag_model_manager(self):
        return ag_models.SubmissionGroup.objects


class SubmissionGroupInvitationSerializer(AGModelSerializer):
    def get_ag_model_manager(self):
        return ag_models.SubmissionGroupInvitation.objects


class SubmissionSerializer(AGModelSerializer):
    def __init__(self, *args, **kwargs):
        data = kwargs.pop('data', None)
        if data is None:
            return super().__init__(*args, **kwargs)

        try:
            # If this fails, then we know we don't have a query dict.
            fixed_data = data.dict()
            fixed_data['submitted_files'] = data.getlist('submitted_files')
        except AttributeError:
            fixed_data = data

        return super().__init__(*args, data=fixed_data, **kwargs)

    def get_ag_model_manager(self):
        return ag_models.Submission.objects


class NotificationSerializer(AGModelSerializer):
    def get_ag_model_manager(self):
        return ag_models.Notification.objects
