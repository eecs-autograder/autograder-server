import random
import string

from django.core import exceptions
from django.test import TestCase

from .models import _DummyAutograderModel, _DummyForeignAutograderModel


class AGModelBaseToDictTest(TestCase):
    def setUp(self):
        super().setUp()
        self.ag_model = _DummyAutograderModel(pos_num_val=15,
                                              non_empty_str_val='spam')

    def test_default_include_fields(self):
        result = self.ag_model.to_dict()
        expected = {
            'pos_num_val': self.ag_model.pos_num_val,
            'non_empty_str_val': self.ag_model.non_empty_str_val,
            'the_answer': self.ag_model.the_answer
        }
        self.assertEqual(expected, result)

    def test_include_fields(self):
        result = self.ag_model.to_dict(
            include_fields=['pos_num_val', 'the_answer'])
        expected = {
            'pos_num_val': self.ag_model.pos_num_val,
            'the_answer': self.ag_model.the_answer
        }
        self.assertEqual(expected, result)

    def test_exclude_fields(self):
        result = self.ag_model.to_dict(
            exclude_fields=['pos_num_val', 'the_answer'])
        expected = {
            'non_empty_str_val': self.ag_model.non_empty_str_val
        }
        self.assertEqual(expected, result)

    def test_include_and_exclude_fields(self):
        include = ['pos_num_val', 'non_empty_str_val', 'the_answer']
        exclude = ['non_empty_str_val', 'the_answer']
        result = self.ag_model.to_dict(include_fields=include,
                                       exclude_fields=exclude)
        expected = {
            'pos_num_val': self.ag_model.pos_num_val
        }
        self.assertEqual(expected, result)

    def test_error_bad_include_field_name(self):
        with self.assertRaises(exceptions.ValidationError):
            self.ag_model.to_dict(
                include_fields=['pos_num_val', 'not_a_field_name'])

    def test_no_error_bad_exclude_field_name(self):
        result = self.ag_model.to_dict(
            exclude_fields=['pos_num_val', 'the_answer', 'not_a_field_name'])
        expected = {
            'non_empty_str_val': self.ag_model.non_empty_str_val
        }
        self.assertEqual(expected, result)

    def test_to_one_serialized_as_pk(self):
        self.ag_model.save()

        related = _DummyForeignAutograderModel(
            name='steve',
            one_to_one=self.ag_model,
            foreign_key=self.ag_model)

        expected = {
            'name': related.name,
            'one_to_one': self.ag_model.pk,
            'foreign_key': self.ag_model.pk,
            'nullable_one_to_one': None,
        }
        result = related.to_dict()

        self.assertEqual(expected, result)


class AGModelValidateAndCreateTestCase(TestCase):
    def test_valid_create(self):
        num_val = random.randint(0, 100)
        str_val = random.choice(string.ascii_letters)
        ag_model = _DummyAutograderModel.objects.validate_and_create(
            pos_num_val=num_val,
            non_empty_str_val=str_val)

        ag_model.refresh_from_db()

        self.assertEqual(num_val, ag_model.pos_num_val)
        self.assertEqual(str_val, ag_model.non_empty_str_val)

    def test_invalid_create(self):
        with self.assertRaises(exceptions.ValidationError) as cm:
            _DummyAutograderModel.objects.validate_and_create(
                pos_num_val=-42,
                non_empty_str_val='')

        self.assertIn('pos_num_val', cm.exception.message_dict)
        self.assertIn('non_empty_str_val', cm.exception.message_dict)

        with self.assertRaises(exceptions.ObjectDoesNotExist):
            _DummyAutograderModel.objects.get(non_empty_str_val='')


class AGModelValidateAndUpdateTestCase(TestCase):
    def setUp(self):
        super().setUp()

        self.ag_model = _DummyAutograderModel.objects.validate_and_create(
            pos_num_val=15,
            non_empty_str_val='spam')

    def test_valid_update(self):
        new_num = random.randint(100, 200)
        new_str = random.choice(string.ascii_letters)
        self.ag_model.validate_and_update(pos_num_val=new_num,
                                          non_empty_str_val=new_str)
        self.ag_model.refresh_from_db()
        self.assertEqual(new_num, self.ag_model.pos_num_val)
        self.assertEqual(new_str, self.ag_model.non_empty_str_val)

        second_new_num = new_num + 1
        self.ag_model.validate_and_update(pos_num_val=second_new_num)
        self.ag_model.refresh_from_db()
        self.assertEqual(second_new_num, self.ag_model.pos_num_val)

    def test_invalid_update_bad_values(self):
        old_vals = self.ag_model.to_dict()

        with self.assertRaises(exceptions.ValidationError) as cm:
            self.ag_model.validate_and_update(pos_num_val=-42,
                                              non_empty_str_val='')

        self.assertIn('pos_num_val', cm.exception.message_dict)
        self.assertIn('non_empty_str_val', cm.exception.message_dict)

        self.ag_model.refresh_from_db()
        self.assertEqual(old_vals, self.ag_model.to_dict())

    def test_invalid_update_nonexistant_field(self):
        with self.assertRaises(exceptions.ValidationError):
            self.ag_model.validate_and_update(not_a_field_name='spam')
