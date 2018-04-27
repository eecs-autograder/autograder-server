import autograder.core.models as ag_models

from .ag_model_serializer import AGModelSerializer


class CourseSerializer(AGModelSerializer):
    ag_model_class = ag_models.Course


class ProjectSerializer(AGModelSerializer):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if not self.context:
            self.show_closing_time = None
            return

        request = self.context['request']
        try:
            self.show_closing_time = self.instance.course.is_admin(request.user)
        except AttributeError:
            # self.instance is a QuerySet, don't show closing time
            # for any of the results.
            self.show_closing_time = False

    def to_representation(self, obj):
        result = super().to_representation(obj)
        if self.show_closing_time is not None and not self.show_closing_time:
            result.pop('closing_time', None)

        return result

    ag_model_class = ag_models.Project


class InstructorFileSerializer(AGModelSerializer):
    ag_model_class = ag_models.InstructorFile


class ExpectedStudentFileSerializer(AGModelSerializer):
    ag_model_class = ag_models.ExpectedStudentFile


class DownloadTaskSerializer(AGModelSerializer):
    ag_model_class = ag_models.DownloadTask


class SubmissionGroupSerializer(AGModelSerializer):
    ag_model_class = ag_models.Group


class SubmissionGroupInvitationSerializer(AGModelSerializer):
    ag_model_class = ag_models.GroupInvitation


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

    ag_model_class = ag_models.Submission


class AGTestSuiteSerializer(AGModelSerializer):
    ag_model_class = ag_models.AGTestSuite


class AGTestCaseSerializer(AGModelSerializer):
    ag_model_class = ag_models.AGTestCase


class AGTestCommandSerializer(AGModelSerializer):
    ag_model_class = ag_models.AGTestCommand


class StudentTestSuiteSerializer(AGModelSerializer):
    ag_model_class = ag_models.StudentTestSuite


class RerunSubmissionTaskSerializer(AGModelSerializer):
    ag_model_class = ag_models.RerunSubmissionsTask


class NotificationSerializer(AGModelSerializer):
    ag_model_class = ag_models.Notification
