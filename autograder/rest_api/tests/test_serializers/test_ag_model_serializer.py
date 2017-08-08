import random

from rest_framework import request, serializers
from rest_framework.test import APIRequestFactory

from autograder.core.tests.test_models.models import (
    _DummyAutograderModel, _DummyForeignAutograderModel)

from autograder.rest_api.serializers.ag_model_serializer import (
    AGModelSerializer)

from .serializer_test_case import SerializerTestCase


class _DummyAGModelSerialier(AGModelSerializer):
    def get_ag_model_manager(self):
        return _DummyAutograderModel.objects


class AGModelSerializerTestCase(SerializerTestCase):
    def setUp(self):
        super().setUp()
        self.kwargs = {
            'pos_num_val': 42,
            'non_empty_str_val': "spam",
            'one_to_one': _DummyForeignAutograderModel.objects.create(name='a;dkfjads'),
            'foreign_key': _DummyForeignAutograderModel.objects.create(name='aasdfa;liejf')
        }

    def test_serialize(self):
        ag_model = _DummyAutograderModel.objects.validate_and_create(**self.kwargs)
        self.do_basic_serialize_test(ag_model, _DummyAGModelSerialier)

    def test_create(self):
        original_count = _DummyAutograderModel.objects.count()
        serializer = _DummyAGModelSerialier(data=self.kwargs)

        self.assertTrue(serializer.is_valid())
        created = serializer.save()
        created.refresh_from_db()

        self.assertEqual(original_count + 1,
                         _DummyAutograderModel.objects.count())
        self.assertEqual(self.kwargs['non_empty_str_val'],
                         created.non_empty_str_val)

    def test_create_with_field_errors(self):
        original_count = _DummyAutograderModel.objects.count()
        self.kwargs['non_empty_str_val'] = ''
        self.kwargs['pos_num_val'] = -2
        with self.assertRaises(serializers.ValidationError):
            serializer = _DummyAGModelSerialier(
                data=self.kwargs)

            self.assertTrue(serializer.is_valid())
            serializer.save()

        self.assertEqual(original_count, _DummyAutograderModel.objects.count())

    def test_update(self):
        ag_model = _DummyAutograderModel.objects.validate_and_create(**self.kwargs)
        new_pos_num_val = random.randint(1000, 9000)
        serializer = _DummyAGModelSerialier(
            ag_model,
            data={'pos_num_val': new_pos_num_val},
            partial=True)

        self.assertTrue(serializer.is_valid())
        serializer.save()

        ag_model.refresh_from_db()

        self.assertEqual(new_pos_num_val, ag_model.pos_num_val)

    def test_update_with_field_errors(self):
        ag_model = _DummyAutograderModel.objects.validate_and_create(**self.kwargs)
        bad_pos_num_val = -8
        with self.assertRaises(serializers.ValidationError):
            serializer = _DummyAGModelSerialier(
                ag_model,
                data={'pos_num_val': bad_pos_num_val},
                partial=True)

            self.assertTrue(serializer.is_valid())
            serializer.save()

        ag_model.refresh_from_db()
        self.assertNotEqual(bad_pos_num_val, self.kwargs['pos_num_val'])
