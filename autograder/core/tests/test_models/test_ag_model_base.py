import random
import string

from django.contrib.auth.models import User
from django.core import exceptions

from autograder.core.models.ag_model_base import AutograderModel
from autograder.utils.testing import UnitTestBase

from .models import (
    _DummyAutograderModel, _DummyForeignAutograderModel, _DummyToManyModel)


# class _SetUp(UnitTestBase):
#     def setUp(self):
#         super().setUp()
#
#         self.many_to_manys = [
#             _DummyToManyModel.objects.create(name='many_thing{}'.format(i))
#             for i in range(4)]
#
#         self.manys_serialized = [obj.to_dict() for obj in self.many_to_manys]


class AGModelBaseToDictTest(UnitTestBase):
    def setUp(self):
        super().setUp()

        self.ag_model = _DummyAutograderModel.objects.create(
            pos_num_val=15,
            non_empty_str_val='spam',
            one_to_one=_DummyForeignAutograderModel.objects.create(name='akdsjhfalsd'),
            foreign_key=_DummyForeignAutograderModel.objects.create(name='bekjfahsdf'))

        self.many_to_manys = [
            _DummyToManyModel.objects.create(name='wee{}'.format(i)) for i in range(3)]
        self.ag_model.many_to_many.set(self.many_to_manys, clear=True)

        # Users aren't AG models and don't have .to_dict()
        self.users = [
            User.objects.create(username='usr{}'.format(i)) for i in range(2)]
        self.ag_model.users.set(self.users, clear=True)

    def test_to_one_and_to_many_default_serialized_as_pk(self):
        expected = {
            'pk': self.ag_model.pk,
            'pos_num_val': self.ag_model.pos_num_val,
            'non_empty_str_val': self.ag_model.non_empty_str_val,
            'the_answer': 42,

            'one_to_one': self.ag_model.one_to_one.pk,
            'nullable_one_to_one': None,

            'foreign_key': self.ag_model.foreign_key.pk,
            'nullable_foreign_key': None,

            'many_to_many': [obj.pk for obj in self.many_to_manys],

            'users': [user.pk for user in self.users]
        }
        result = self.ag_model.to_dict()
        result['users'].sort()

        print(result)
        self.assertEqual(expected, result)

    def test_to_one_and_to_many_in_serialize_related(self):
        _DummyAutograderModel.SERIALIZE_RELATED = (
            'one_to_one', 'nullable_one_to_one', 'foreign_key', 'many_to_many')
        expected = {
            'pk': self.ag_model.pk,
            'pos_num_val': self.ag_model.pos_num_val,
            'non_empty_str_val': self.ag_model.non_empty_str_val,
            'the_answer': 42,

            'one_to_one': self.ag_model.one_to_one.to_dict(),
            'nullable_one_to_one': None,

            'foreign_key': self.ag_model.foreign_key.to_dict(),
            'nullable_foreign_key': None,

            'many_to_many': [obj.to_dict() for obj in self.many_to_manys],

            'users': [user.pk for user in self.users]
        }

        result = self.ag_model.to_dict()
        result['users'].sort()

        print(result)
        self.assertEqual(expected, result)

    def test_empty_to_many_serialized_correctly(self):
        self.ag_model.many_to_many.clear()
        self.assertSequenceEqual([], self.ag_model.to_dict()['many_to_many'])


# class AGModelValidateAndCreateTestCase(_SetUp):
#     def test_valid_create(self):
#         num_val = random.randint(0, 100)
#         str_val = random.choice(string.ascii_letters)
#         ag_model = _DummyAutograderModel.objects.validate_and_create(
#             pos_num_val=num_val,
#             non_empty_str_val=str_val,
#             many_to_many=self.many_to_manys)
#
#         ag_model.refresh_from_db()
#
#         self.assertEqual(num_val, ag_model.pos_num_val)
#         self.assertEqual(str_val, ag_model.non_empty_str_val)
#         self.assertCountEqual(self.many_to_manys, ag_model.many_to_many.all())
#
#     def test_invalid_create_bad_values(self):
#         with self.assertRaises(exceptions.ValidationError) as cm:
#             _DummyAutograderModel.objects.validate_and_create(
#                 pos_num_val=-42,
#                 non_empty_str_val='')
#
#         self.assertIn('pos_num_val', cm.exception.message_dict)
#         self.assertIn('non_empty_str_val', cm.exception.message_dict)
#
#         with self.assertRaises(exceptions.ObjectDoesNotExist):
#             _DummyAutograderModel.objects.get(non_empty_str_val='')
#
#     def test_create_to_one_and_to_many_loaded_from_pk(self):
#         self.fail()
#
#     def test_create_to_one_and_to_many_in_serialize_related(self):
#         self.fail()
#
#
# class AGModelValidateAndUpdateTestCase(_SetUp):
#     def setUp(self):
#         super().setUp()
#
#         self.ag_model = _DummyAutograderModel.objects.validate_and_create(
#             pos_num_val=15,
#             non_empty_str_val='spam',
#             read_only_field='blah',
#             many_to_many=[_DummyToManyModel.objects.create(name='waaaluigi')])
#
#         self.assertEqual(1, self.ag_model.many_to_many.count())
#
#     def test_valid_update(self):
#         new_num = random.randint(100, 200)
#         new_str = random.choice(string.ascii_letters)
#         self.ag_model.validate_and_update(
#             pos_num_val=new_num, non_empty_str_val=new_str,
#             many_to_many=self.many_to_manys)
#
#         self.ag_model.refresh_from_db()
#         self.assertEqual(new_num, self.ag_model.pos_num_val)
#         self.assertEqual(new_str, self.ag_model.non_empty_str_val)
#         self.assertCountEqual(self.many_to_manys,
#                               self.ag_model.many_to_many.all())
#
#         second_new_num = new_num + 1
#         self.ag_model.validate_and_update(pos_num_val=second_new_num)
#         self.ag_model.refresh_from_db()
#         self.assertEqual(second_new_num, self.ag_model.pos_num_val)
#
#     def test_updated_to_one_and_to_many_loaded_from_pk(self):
#         self.fail()
#
#     def test_update_to_one_and_to_many_in_serialize_related(self):
#         self.fail()
#
#     def test_invalid_update_bad_values(self):
#         old_vals = self.ag_model.to_dict()
#
#         with self.assertRaises(exceptions.ValidationError) as cm:
#             self.ag_model.validate_and_update(pos_num_val=-42,
#                                               non_empty_str_val='')
#
#         self.assertIn('pos_num_val', cm.exception.message_dict)
#         self.assertIn('non_empty_str_val', cm.exception.message_dict)
#
#         self.ag_model.refresh_from_db()
#         self.assertDictContentsEqual(old_vals, self.ag_model.to_dict())
#
#     def test_invalid_update_nonexistant_field(self):
#         with self.assertRaises(exceptions.ValidationError) as cm:
#             self.ag_model.validate_and_update(not_a_field_name='spam')
#
#         self.assertIn(
#             'not_a_field_name',
#             cm.exception.message_dict[AutograderModel.INVALID_FIELD_NAMES_KEY])
#
#     def test_invalid_update_non_editable_field(self):
#         with self.assertRaises(exceptions.ValidationError) as cm:
#             self.ag_model.validate_and_update(read_only_field='steve')
#
#         self.assertIn('non_editable_fields', cm.exception.message_dict)
#         self.assertIn('read_only_field',
#                       cm.exception.message_dict['non_editable_fields'])
