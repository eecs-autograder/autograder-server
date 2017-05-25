import copy

from django.db import transaction

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


class AutograderTestCaseSerializer(AGModelSerializer):
    def __init__(self, *args, **kwargs):
        if 'data' not in kwargs:
            super().__init__(*args, **kwargs)
            return

        data = copy.copy(kwargs.pop('data'))
        for fdbk_field in ag_models.AutograderTestCaseBase.FDBK_FIELD_NAMES:
            if fdbk_field in data:
                data[fdbk_field] = (
                    ag_models.FeedbackConfig.objects.validate_and_create(
                        **data[fdbk_field]))

        super().__init__(*args, data=data, **kwargs)

    def validate_and_create(self, data):
        return ag_models.AutograderTestCaseFactory.validate_and_create(**data)

    def create(self, validated_data):
        with transaction.atomic():
            file_field_data = self._deserialize_related_file_fields(validated_data)
            result = super().create(validated_data)
            for field_name, vals in file_field_data.items():
                getattr(result, field_name).set(vals, clear=True)

            return result

    def update(self, instance, validated_data):
        with transaction.atomic():
            file_field_data = self._deserialize_related_file_fields(validated_data)
            result = super().update(instance, validated_data)
            for field_name, vals in file_field_data.items():
                getattr(result, field_name).set(vals, clear=True)

            return result

    def _deserialize_related_file_fields(self, data):
        result = {}
        if 'test_resource_files' in data:
            result['test_resource_files'] = self._load_uploaded_files(
                data.pop('test_resource_files'))

        if 'student_resource_files' in data:
            result['student_resource_files'] = self._load_patterns(
                data.pop('student_resource_files'))

        if 'project_files_to_compile_together' in data:
            result['project_files_to_compile_together'] = self._load_uploaded_files(
                data.pop('project_files_to_compile_together'))

        if 'student_files_to_compile_together' in data:
            result['student_files_to_compile_together'] = self._load_patterns(
                data.pop('student_files_to_compile_together'))

        return result

    def _load_uploaded_files(self, dicts):
        try:
            pk_list = [obj['pk'] for obj in dicts]
        except TypeError:
            pk_list = [obj.pk for obj in dicts]

        return ag_models.UploadedFile.objects.filter(
            pk__in=pk_list)

    def _load_patterns(self, dicts):
        try:
            pk_list = [obj['pk'] for obj in dicts]
        except TypeError:
            pk_list = [obj.pk for obj in dicts]

        return ag_models.ExpectedStudentFilePattern.objects.filter(
            pk__in=pk_list)


class AutograderTestResultSerializer(AGModelSerializer):
    def __init__(self, *args, feedback_type=None, **kwargs):
        if feedback_type is None:
            raise ValueError(
                'Missing feedback_type in AGTestResulSerializer initialization')

        self._fdbk_type = feedback_type

        super().__init__(*args, **kwargs)

    def save(self, *args, **kwargs):
        raise NotImplementedError(
            'Creating or updating AG test results is not supported')

    def create(self, validated_data):
        raise NotImplementedError('Updating AG test results is not supported')

    def update(self, instance, validated_data):
        raise NotImplementedError('Creating AG test results is not supported')

    def to_representation(self, obj):
        if self._fdbk_type == 'normal':
            return obj.get_normal_feedback().to_dict()

        if self._fdbk_type == 'ultimate_submission':
            return obj.get_ultimate_submission_feedback().to_dict()

        if self._fdbk_type == 'staff_viewer':
            return obj.get_staff_viewer_feedback().to_dict()

        if self._fdbk_type == 'past_submission_limit':
            return obj.get_past_submission_limit_feedback().to_dict()

        if self._fdbk_type == 'max':
            return obj.get_max_feedback().to_dict()

        raise ValueError('Invalid feedback type: {}'.format(self._fdbk_type))


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
