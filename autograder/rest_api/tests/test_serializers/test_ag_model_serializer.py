import random

from django import test
from rest_framework import serializers

from autograder.core.tests.test_models.models import _DummyAutograderModel

from autograder.rest_api.serializers.ag_model_serializer import (
    AGModelSerializer)

from .utils import SerializerTestCase


class _DummyAGModelSerialier(AGModelSerializer):
    def get_ag_model_manager(self):
        return _DummyAutograderModel.objects


class AGModelSerializerTestCase(SerializerTestCase, test.TestCase):
    def setUp(self):
        self.ag_model = _DummyAutograderModel(
            pos_num_val=42,
            non_empty_str_val="spam")

    def test_serialize(self):
        self.do_basic_serialize_test(self.ag_model, _DummyAGModelSerialier)

    def test_create(self):
        self.assertEqual(0, _DummyAutograderModel.objects.count())
        serializer = _DummyAGModelSerialier(data=self.ag_model.to_dict())

        self.assertTrue(serializer.is_valid())
        serializer.save()

        self.assertEqual(1, _DummyAutograderModel.objects.count())
        loaded = _DummyAutograderModel.objects.get(
            pos_num_val=self.ag_model.pos_num_val)
        self.assertEqual(self.ag_model.non_empty_str_val,
                         loaded.non_empty_str_val)

    def test_create_with_field_errors(self):
        with self.assertRaises(serializers.ValidationError):
            serializer = _DummyAGModelSerialier(
                data={'pos_num_val': -2, 'non_empty_str_val': ''})

            self.assertTrue(serializer.is_valid())
            serializer.save()

        self.assertEqual(0, _DummyAutograderModel.objects.count())

    def test_update(self):
        self.ag_model.save()
        new_pos_num_val = random.randint(1000, 9000)
        serializer = _DummyAGModelSerialier(
            self.ag_model,
            data={'pos_num_val': new_pos_num_val},
            partial=True)

        self.assertTrue(serializer.is_valid())
        serializer.save()

        self.ag_model.refresh_from_db()

        self.assertEqual(new_pos_num_val, self.ag_model.pos_num_val)

    def test_update_with_field_errors(self):
        self.ag_model.save()
        bad_pos_num_val = -8
        with self.assertRaises(serializers.ValidationError):
            serializer = _DummyAGModelSerialier(
                self.ag_model,
                data={'pos_num_val': bad_pos_num_val},
                partial=True)

            self.assertTrue(serializer.is_valid())
            serializer.save()

        self.ag_model.refresh_from_db()
        self.assertNotEqual(bad_pos_num_val, self.ag_model.pos_num_val)
