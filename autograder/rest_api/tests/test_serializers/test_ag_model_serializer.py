import random

from rest_framework import request, serializers
from rest_framework.test import APIRequestFactory

from autograder.core.tests.test_models.models import _DummyAutograderModel

from autograder.rest_api.serializers.ag_model_serializer import (
    AGModelSerializer)

from .serializer_test_case import SerializerTestCase


class _DummyAGModelSerialier(AGModelSerializer):
    def get_ag_model_manager(self):
        return _DummyAutograderModel.objects


class AGModelSerializerTestCase(SerializerTestCase):
    def setUp(self):
        super().setUp()
        self.ag_model = _DummyAutograderModel.objects.validate_and_create(
            pos_num_val=42,
            non_empty_str_val="spam")

    def test_serialize(self):
        self.do_basic_serialize_test(self.ag_model, _DummyAGModelSerialier)

    def test_serialize_include_fields(self):
        self.do_include_exclude_fields_from_request_test(
            include_fields=['non_empty_str_val'])

    def test_serialize_exclude_fields(self):
        self.do_include_exclude_fields_from_request_test(
            exclude_fields=['the_answer'])

    def test_serialize_include_and_exclude_fields(self):
        self.do_include_exclude_fields_from_request_test(
            include_fields=['the_answer'], exclude_fields=['pos_num_val'])

    def do_include_exclude_fields_from_request_test(
            self, include_fields=None, exclude_fields=None):
        data = {}
        if include_fields is not None:
            data['include_fields'] = include_fields
        if exclude_fields is not None:
            data['exclude_fields'] = exclude_fields

        get_request = request.Request(
            APIRequestFactory().get('path', data=data))
        serializer = _DummyAGModelSerialier(
            self.ag_model, context={'request': get_request})

        self.assertEqual(self.ag_model.to_dict(include_fields=include_fields,
                                               exclude_fields=exclude_fields),
                         serializer.data)

    def test_create(self):
        original_count = _DummyAutograderModel.objects.count()
        serializer = _DummyAGModelSerialier(data={
            'pos_num_val': 42,
            'non_empty_str_val': "spam"
        })

        self.assertTrue(serializer.is_valid())
        created = serializer.save()
        created.refresh_from_db()

        self.assertEqual(original_count + 1,
                         _DummyAutograderModel.objects.count())
        self.assertEqual(self.ag_model.non_empty_str_val,
                         created.non_empty_str_val)

    def test_create_with_field_errors(self):
        original_count = _DummyAutograderModel.objects.count()
        with self.assertRaises(serializers.ValidationError):
            serializer = _DummyAGModelSerialier(
                data={'pos_num_val': -2, 'non_empty_str_val': ''})

            self.assertTrue(serializer.is_valid())
            serializer.save()

        self.assertEqual(original_count, _DummyAutograderModel.objects.count())

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
