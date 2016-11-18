import copy
import uuid

from django.core.files.uploadedfile import SimpleUploadedFile

import autograder.rest_api.serializers as ag_serializers
import autograder.core.models as ag_models
from autograder.core.models.autograder_test_case import feedback_config

from .serializer_test_case import SerializerTestCase
import autograder.utils.testing.model_obj_builders as obj_build
from autograder.core.tests.test_models.test_autograder_test_case.models \
    import _DummyAutograderTestCase


class _SetUp:
    def setUp(self):
        super().setUp()
        self.project = obj_build.build_project()
        self.expected_pattern = ag_models.ExpectedStudentFilePattern.objects.validate_and_create(
            pattern='spammy', max_num_matches=3,
            project=self.project)
        self.uploaded_file = ag_models.UploadedFile.objects.validate_and_create(
            file_obj=SimpleUploadedFile('filey', b'waaaluigi'),
            project=self.project)


class AGTestCaseSerializerTestCase(_SetUp, SerializerTestCase):
    def test_serialize(self):
        ag_test = _DummyAutograderTestCase.objects.validate_and_create(
            name='steve',
            project=self.project,
            test_resource_files=[self.uploaded_file],
            student_resource_files=[self.expected_pattern],
            project_files_to_compile_together=[self.uploaded_file],
            student_files_to_compile_together=[self.expected_pattern])
        print(ag_test.to_dict(include_fields=['test_resource_files']))
        self.do_basic_serialize_test(ag_test,
                                     ag_serializers.AGTestCaseSerializer)

    def test_create(self):
        self.assertEqual(0, ag_models.AutograderTestCaseBase.objects.count())
        data = {
            'name': 'steve',
            'project': self.project,
            'compiler': 'clang++',
            'type_str': 'compiled_and_run_test_case',
        }

        serializer = ag_serializers.AGTestCaseSerializer(data=data)
        serializer.is_valid()
        serializer.save()

        self.assertEqual(1, ag_models.AutograderTestCaseBase.objects.count())
        loaded = ag_models.AutograderTestCaseBase.objects.get(
            name=data['name'])

        expected = copy.deepcopy(data)
        expected['project'] = data['project'].pk
        expected['pk'] = loaded.pk
        self.assertEqual(
            expected, loaded.to_dict(include_fields=['pk'] + list(data.keys())))

    def test_create_and_update_feedback_configs(self):
        for fdbk_field in ag_models.AutograderTestCaseBase.FDBK_FIELD_NAMES:
            data = {
                'name': 'steve',
                'project': self.project,
                'compiler': 'clang++',
                'type_str': 'compiled_and_run_test_case',
                fdbk_field: (
                    ag_models.FeedbackConfig.create_with_max_fdbk().to_dict())
            }

            serializer = ag_serializers.AGTestCaseSerializer(data=data)
            serializer.is_valid()
            serializer.save()
            loaded = ag_models.AutograderTestCaseBase.objects.get(
                name=data['name'])

            self.assertEqual(data[fdbk_field],
                             getattr(loaded, fdbk_field).to_dict())

            updated_fdbk = copy.copy(data[fdbk_field])
            updated_fdbk['return_code_fdbk'] = (
                feedback_config.ReturnCodeFdbkLevel.no_feedback)
            self.assertNotEqual(data[fdbk_field], updated_fdbk)

            serializer = ag_serializers.AGTestCaseSerializer(
                loaded, data={fdbk_field: updated_fdbk},
                partial=True)
            serializer.is_valid()
            serializer.save()

            loaded.refresh_from_db()
            self.assertEqual(updated_fdbk,
                             getattr(loaded, fdbk_field).to_dict())

            loaded.delete()


class RelatedFileFieldsDeserializeTestCase(_SetUp, SerializerTestCase):
    def setUp(self):
        super().setUp()

        self.base_data = {
            'name': 'test_case',
            'project': self.project,
            'compiler': 'g++',
            'type_str': 'compiled_and_run_test_case',
        }

    def test_create_with_related_file_fields(self):
        compile_uploaded = self.random_uploaded()
        compile_student = self.random_pattern()
        self.base_data.update({
            'test_resource_files': [self.uploaded_file.to_dict()],
            'student_resource_files': [self.expected_pattern.to_dict()],
            'project_files_to_compile_together': [compile_uploaded],
            'student_files_to_compile_together': [compile_student],
        })

        serializer = ag_serializers.AGTestCaseSerializer(data=self.base_data)
        serializer.is_valid()
        serializer.save()

        loaded = ag_models.AutograderTestCaseBase.objects.get(
            name=self.base_data['name'])
        self.assertCountEqual([self.uploaded_file],
                              loaded.test_resource_files.all())
        self.assertCountEqual([self.expected_pattern],
                              loaded.student_resource_files.all())
        self.assertCountEqual([compile_uploaded],
                              loaded.project_files_to_compile_together.all())
        self.assertCountEqual([compile_student],
                              loaded.student_files_to_compile_together.all())

    def test_update_with_related_file_fields(self):
        test_case = ag_models.AutograderTestCaseFactory.validate_and_create(
            **self.base_data)
        for i in range(2):
            test_resource_file = self.random_uploaded()
            student_resource_file = self.random_pattern()
            project_file_to_compile_together = self.random_uploaded()
            student_file_to_compile_together = self.random_pattern()
            updated_data = {
                'test_resource_files': [test_resource_file.to_dict()],
                'student_resource_files': [student_resource_file.to_dict()],
                'project_files_to_compile_together': [
                    project_file_to_compile_together.to_dict()],
                'student_files_to_compile_together': [
                    student_file_to_compile_together.to_dict()]
            }

            serializer = ag_serializers.AGTestCaseSerializer(
                test_case, data=updated_data, partial=True)
            serializer.is_valid()
            serializer.save()

            test_case.refresh_from_db()

            self.assertCountEqual([test_resource_file],
                                  test_case.test_resource_files.all())
            self.assertCountEqual([student_resource_file],
                                  test_case.student_resource_files.all())
            self.assertCountEqual(
                [project_file_to_compile_together],
                test_case.project_files_to_compile_together.all())
            self.assertCountEqual(
                [student_file_to_compile_together],
                test_case.student_files_to_compile_together.all())

    def random_pattern(self):
        return ag_models.ExpectedStudentFilePattern.objects.validate_and_create(
            pattern='pattern{}'.format(uuid.uuid4().hex), project=self.project)

    def random_uploaded(self):
        file_ = SimpleUploadedFile('file{}'.format(uuid.uuid4().hex), b'spam')
        return ag_models.UploadedFile.objects.validate_and_create(
            file_obj=file_, project=self.project)
