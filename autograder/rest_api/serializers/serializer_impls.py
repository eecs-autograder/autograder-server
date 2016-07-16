import copy

from django.http import QueryDict

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
        if 'feedback_configuration' in data:
            data['feedback_configuration'] = (
                ag_models.FeedbackConfig.objects.validate_and_create(
                    **data['feedback_configuration']))

        return super().__init__(*args, data=data, **kwargs)

    def validate_and_create(self, data):
        return ag_models.AutograderTestCaseFactory.validate_and_create(**data)


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
