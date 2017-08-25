import autograder.core.models as ag_models

from .ag_model_serializer import AGModelSerializer


class CourseSerializer(AGModelSerializer):
    def get_ag_model_manager(self):
        return ag_models.Course.objects


class ProjectSerializer(AGModelSerializer):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if not self.context:
            self.show_closing_time = None
            return

        request = self.context['request']
        try:
            self.show_closing_time = self.instance.course.is_administrator(request.user)
        except AttributeError:
            # self.instance is a QuerySet, don't show closing time
            # for any of the results.
            self.show_closing_time = False

    def to_representation(self, obj):
        result = super().to_representation(obj)
        if self.show_closing_time is not None and not self.show_closing_time:
            result.pop('closing_time', None)

        return result

    def get_ag_model_manager(self):
        return ag_models.Project.objects


class UploadedFileSerializer(AGModelSerializer):
    def get_ag_model_manager(self):
        return ag_models.UploadedFile.objects


class ExpectedStudentFilePatternSerializer(AGModelSerializer):
    def get_ag_model_manager(self):
        return ag_models.ExpectedStudentFilePattern.objects


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
            super().__init__(*args, **kwargs)
            return

        try:
            # If this fails, then we know we don't have a query dict.
            fixed_data = data.dict()
            fixed_data['submitted_files'] = data.getlist('submitted_files')
        except AttributeError:
            fixed_data = data

        super().__init__(*args, data=fixed_data, **kwargs)

    def get_ag_model_manager(self):
        return ag_models.Submission.objects


class AGTestSuiteSerializer(AGModelSerializer):
    def get_ag_model_manager(self):
        return ag_models.AGTestSuite.objects


class AGTestCaseSerializer(AGModelSerializer):
    def get_ag_model_manager(self):
        return ag_models.AGTestCase.objects


class AGTestCommandSerializer(AGModelSerializer):
    def get_ag_model_manager(self):
        return ag_models.AGTestCommand.objects


class NotificationSerializer(AGModelSerializer):
    def get_ag_model_manager(self):
        return ag_models.Notification.objects
