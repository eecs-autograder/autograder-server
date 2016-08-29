import random
import string

from django.contrib.auth.models import User
from django.core import exceptions

from autograder.utils.testing import UnitTestBase

from .models import (
    _DummyAutograderModel, _DummyForeignAutograderModel, _DummyToManyModel)


class _SetUp:
    def setUp(self):
        super().setUp()

        self.many_to_manys = [
            _DummyToManyModel.objects.create(name='many_thing{}'.format(i))
            for i in range(4)]

        self.manys_serialized = [obj.to_dict() for obj in self.many_to_manys]


class AGModelBaseToDictTest(_SetUp, UnitTestBase):
    def setUp(self):
        super().setUp()
        self.ag_model = _DummyAutograderModel.objects.create(
            pos_num_val=15, non_empty_str_val='spam')
        self.users = [
            User.objects.create(username='usr{}'.format(i)) for i in range(3)]
        self.ag_model.users.set(self.users, clear=True)

    def test_default_include_fields(self):
        self.ag_model.many_to_many.set(self.many_to_manys, clear=True)
        result = self.ag_model.to_dict()
        expected = {
            'pk': self.ag_model.pk,
            'pos_num_val': self.ag_model.pos_num_val,
            'non_empty_str_val': self.ag_model.non_empty_str_val,
            'the_answer': self.ag_model.the_answer,
            'many_to_many': self.manys_serialized,
            'users': self.users
        }
        print(result)
        self.assertContentsEqual(expected, result)

    def test_include_fields(self):
        self.ag_model.many_to_many.set(self.many_to_manys, clear=True)
        result = self.ag_model.to_dict(
            include_fields=['pos_num_val', 'many_to_many'])
        expected = {
            'pk': self.ag_model.pk,
            'pos_num_val': self.ag_model.pos_num_val,
            'many_to_many': self.manys_serialized
        }
        self.assertContentsEqual(expected, result)

    def test_exclude_fields(self):
        result = self.ag_model.to_dict(
            exclude_fields=['pos_num_val', 'the_answer', 'many_to_many'])
        expected = {
            'pk': self.ag_model.pk,
            'non_empty_str_val': self.ag_model.non_empty_str_val,
            'users': self.users
        }
        self.assertContentsEqual(expected, result)

    def test_include_and_exclude_fields(self):
        include = ['pos_num_val', 'non_empty_str_val', 'the_answer']
        exclude = ['non_empty_str_val', 'the_answer']
        result = self.ag_model.to_dict(include_fields=include,
                                       exclude_fields=exclude)
        expected = {
            'pk': self.ag_model.pk,
            'pos_num_val': self.ag_model.pos_num_val
        }
        self.assertEqual(expected, result)

    def test_error_bad_include_field_name(self):
        with self.assertRaises(exceptions.ValidationError) as cm:
            self.ag_model.to_dict(
                include_fields=['pos_num_val', 'not_a_field_name'])

        self.assertIn('invalid_field_names', cm.exception.message_dict)
        self.assertIn('not_a_field_name',
                      cm.exception.message_dict['invalid_field_names'])

    def test_no_error_bad_exclude_field_name(self):
        result = self.ag_model.to_dict(
            exclude_fields=['pos_num_val', 'the_answer', 'not_a_field_name', 'users'])
        expected = {
            'pk': self.ag_model.pk,
            'non_empty_str_val': self.ag_model.non_empty_str_val,
            'many_to_many': []
        }
        self.assertEqual(expected, result)

    def test_to_one_serialized_as_pk(self):
        self.ag_model.save()

        related = _DummyForeignAutograderModel(
            name='steve',
            one_to_one=self.ag_model,
            foreign_key=self.ag_model)

        expected = {
            'pk': related.pk,
            'name': related.name,
            'one_to_one': self.ag_model.pk,
            'foreign_key': self.ag_model.pk,
            'nullable_one_to_one': None,
        }
        result = related.to_dict()

        self.assertEqual(expected, result)


class AGModelValidateAndCreateTestCase(_SetUp, UnitTestBase):
    def test_valid_create(self):
        num_val = random.randint(0, 100)
        str_val = random.choice(string.ascii_letters)
        ag_model = _DummyAutograderModel.objects.validate_and_create(
            pos_num_val=num_val,
            non_empty_str_val=str_val,
            many_to_many=self.many_to_manys)

        ag_model.refresh_from_db()

        self.assertEqual(num_val, ag_model.pos_num_val)
        self.assertEqual(str_val, ag_model.non_empty_str_val)
        self.assertCountEqual(self.many_to_manys, ag_model.many_to_many.all())

    def test_invalid_create(self):
        with self.assertRaises(exceptions.ValidationError) as cm:
            _DummyAutograderModel.objects.validate_and_create(
                pos_num_val=-42,
                non_empty_str_val='')

        self.assertIn('pos_num_val', cm.exception.message_dict)
        self.assertIn('non_empty_str_val', cm.exception.message_dict)

        with self.assertRaises(exceptions.ObjectDoesNotExist):
            _DummyAutograderModel.objects.get(non_empty_str_val='')


class AGModelValidateAndUpdateTestCase(_SetUp, UnitTestBase):
    def setUp(self):
        super().setUp()

        self.ag_model = _DummyAutograderModel.objects.validate_and_create(
            pos_num_val=15,
            non_empty_str_val='spam',
            read_only_field='blah',
            many_to_many=[_DummyToManyModel.objects.create(name='waaaluigi')])

        self.assertEqual(1, self.ag_model.many_to_many.count())

    def test_valid_update(self):
        new_num = random.randint(100, 200)
        new_str = random.choice(string.ascii_letters)
        self.ag_model.validate_and_update(
            pos_num_val=new_num, non_empty_str_val=new_str,
            many_to_many=self.many_to_manys)

        self.ag_model.refresh_from_db()
        self.assertEqual(new_num, self.ag_model.pos_num_val)
        self.assertEqual(new_str, self.ag_model.non_empty_str_val)
        self.assertCountEqual(self.many_to_manys,
                              self.ag_model.many_to_many.all())

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
        self.assertContentsEqual(old_vals, self.ag_model.to_dict())

    def test_invalid_update_nonexistant_field(self):
        with self.assertRaises(exceptions.ValidationError):
            self.ag_model.validate_and_update(not_a_field_name='spam')

    def test_invalid_update_non_editable_field(self):
        with self.assertRaises(exceptions.ValidationError) as cm:
            self.ag_model.validate_and_update(read_only_field='steve')

        self.assertIn('non_editable_fields', cm.exception.message_dict)
        self.assertIn('read_only_field',
                      cm.exception.message_dict['non_editable_fields'])
