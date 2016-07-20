import copy

import autograder.rest_api.serializers as ag_serializers
import autograder.core.models as ag_models
from autograder.core.models.autograder_test_case import feedback_config

from .serializer_test_case import SerializerTestCase
import autograder.core.tests.dummy_object_utils as obj_ut
from autograder.core.tests.test_models.test_autograder_test_case.models \
    import _DummyAutograderTestCase


class AGTestCaseSerializerTestCase(SerializerTestCase):
    def setUp(self):
        super().setUp()
        self.project = obj_ut.build_project()

    def test_serialize(self):
        ag_test = _DummyAutograderTestCase.objects.validate_and_create(
            name='steve',
            project=self.project)
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
        self.assertEqual(expected, loaded.to_dict(include_fields=data.keys()))

    def test_create_and_update_feedback_configs(self):
        for fdbk_field in ag_models.AutograderTestCaseBase.FBDK_FIELD_NAMES:
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
