from django.core import exceptions
import requests

import autograder.core.models as ag_models

from .ag_model_serializer import AGModelSerializer


class CourseSerializer(AGModelSerializer):
    ag_model_class = ag_models.Course


class ProjectSerializer(AGModelSerializer):
    ag_model_class = ag_models.Project

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._course = None

        if isinstance(self.instance, ag_models.Project):
            self._course = self.instance.course
        elif self.instance:  # could be empty QuerySet, None, or empty list
            self._course = self.instance[0].course

    def to_representation(self, obj):
        result = super().to_representation(obj)
        if not self.context:
            return result

        if self._course is None and isinstance(obj, ag_models.Project):
            self._course = obj.course

        if self._course is not None and not self._course.is_admin(self.context['request'].user):
            result.pop('closing_time', None)

        if self._course is not None and not self._course.is_staff(self.context['request'].user):
            result.pop('instructor_files', None)

        return result


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


class SandboxDockerImageSerializer(AGModelSerializer):
    ag_model_class = ag_models.SandboxDockerImage


class BuildSandboxDockerImageTaskSerializer(AGModelSerializer):
    ag_model_class = ag_models.BuildSandboxDockerImageTask


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
