import copy
import enum
from typing import Any, Callable, Dict, List, cast
from unittest import mock

from django.contrib.auth.models import User
from django.core import exceptions
from django.test import SimpleTestCase

from autograder.core.models.ag_model_base import AutograderModel, DictSerializable
from autograder.utils.testing import UnitTestBase

from .models import (
    AGModelWithDecimalField, AGModelWithSerializableField, AnEnum, DictSerializableClass,
    DummyAutograderModel, DummyForeignAutograderModel, DummyToManyModel
)


class AGModelBaseToDictTest(UnitTestBase):
    ag_model: DummyAutograderModel
    many_to_manys: List[DummyToManyModel]
    users: List[User]

    def setUp(self) -> None:
        super().setUp()

        self.maxDiff = None

        self.ag_model = DummyAutograderModel.objects.create(
            pos_num_val=15,
            non_empty_str_val='spam',
            one_to_one=DummyForeignAutograderModel.objects.create(name='akdsjhfalsd'),
            foreign_key=DummyForeignAutograderModel.objects.create(name='bekjfahsdf'))

        self.many_to_manys = [
            DummyToManyModel.objects.create(name='wee{}'.format(i)) for i in range(3)]
        self.ag_model.many_to_many.set(self.many_to_manys, clear=True)

        # Users aren't AG models and don't have .to_dict()
        self.users = [
            User.objects.create(username='usr{}'.format(i)) for i in range(2)]
        self.ag_model.users.set(self.users, clear=True)

    def test_to_one_and_to_many_default_serialized_as_pk(self) -> None:
        expected = {
            'pk': self.ag_model.pk,
            'pos_num_val': self.ag_model.pos_num_val,
            'non_empty_str_val': self.ag_model.non_empty_str_val,
            'the_answer': 42,
            'enum_property': 'egg',

            'enum_field': 'spam',

            'one_to_one': self.ag_model.one_to_one.pk,
            'one_to_one_id': self.ag_model.one_to_one.pk,
            'nullable_one_to_one': None,
            'nullable_one_to_one_id': None,

            'foreign_key': self.ag_model.foreign_key.pk,
            'foreign_key_id': self.ag_model.foreign_key.pk,
            'nullable_foreign_key': None,
            'nullable_foreign_key_id': None,

            'many_to_many': [obj.pk for obj in self.many_to_manys],
            'another_many_to_many': [],

            'users': list(sorted(user.pk for user in self.users))
        }
        result = self.ag_model.to_dict()
        print(result)
        self.assertEqual(expected, result)

        expected_one_to_many = {
            'pk': self.ag_model.foreign_key.pk,
            'name': self.ag_model.foreign_key.name,
            'rev_foreign_key': [self.ag_model.pk]
        }
        self.assertEqual(expected_one_to_many, self.ag_model.foreign_key.to_dict())

    def test_to_one_and_to_many_in_serialize_related(self) -> None:
        serialize_related = ('one_to_one', 'nullable_one_to_one', 'foreign_key', 'many_to_many')
        target = 'autograder.core.tests.test_models.models.DummyAutograderModel.SERIALIZE_RELATED'
        with mock.patch(target, new=serialize_related):
            expected = {
                'pk': self.ag_model.pk,
                'pos_num_val': self.ag_model.pos_num_val,
                'non_empty_str_val': self.ag_model.non_empty_str_val,
                'the_answer': 42,
                'enum_property': 'egg',

                'enum_field': 'spam',

                'one_to_one': self.ag_model.one_to_one.to_dict(),
                'one_to_one_id': self.ag_model.one_to_one.pk,
                'nullable_one_to_one': None,
                'nullable_one_to_one_id': None,

                'foreign_key': self.ag_model.foreign_key.to_dict(),
                'foreign_key_id': self.ag_model.foreign_key.pk,
                'nullable_foreign_key': None,
                'nullable_foreign_key_id': None,

                'many_to_many': [obj.to_dict() for obj in self.many_to_manys],
                'another_many_to_many': [],

                'users': list(sorted(user.pk for user in self.users))
            }

            result = self.ag_model.to_dict()
            print(result)
            self.assertEqual(expected, result)

        target = ('autograder.core.tests.test_models.models.'
                  'DummyForeignAutograderModel.SERIALIZE_RELATED')
        with mock.patch(target, new=('rev_foreign_key',)):
            expected_one_to_many = {
                'pk': self.ag_model.foreign_key.pk,
                'name': self.ag_model.foreign_key.name,
                'rev_foreign_key': [self.ag_model.to_dict()]
            }
            self.assertEqual(expected_one_to_many, self.ag_model.foreign_key.to_dict())

    def test_empty_to_many_serialized_correctly(self) -> None:
        self.ag_model.many_to_many.clear()
        self.assertSequenceEqual([], cast(List[User], self.ag_model.to_dict()['many_to_many']))

    def test_decimal_field_serialized_as_string(self) -> None:
        obj = AGModelWithDecimalField.objects.validate_and_create(decimal_field=.5)
        self.assertEqual('0.50', obj.to_dict()['decimal_field'])

        obj = AGModelWithDecimalField.objects.validate_and_create(decimal_field='.5')
        self.assertEqual('0.50', obj.to_dict()['decimal_field'])


class AGModelValidateAndCreateTestCase(UnitTestBase):
    many_to_manys: List[DummyToManyModel]
    users: List[User]

    def setUp(self) -> None:
        super().setUp()

        self.many_to_manys = [
            DummyToManyModel.objects.create(name='wee{}'.format(i)) for i in range(3)]
        self.users = [
            User.objects.create(username='usr{}'.format(i)) for i in range(2)]

    def test_valid_create(self) -> None:
        num_val = 827349
        str_val = 'badsvihajhfs'

        one_to_one = DummyForeignAutograderModel.objects.create(name='akjdnkajhsdf')
        foreign_key = DummyForeignAutograderModel.objects.create(name='qbdbfakdfl')

        ag_model = DummyAutograderModel.objects.validate_and_create(
            pos_num_val=num_val,
            non_empty_str_val=str_val,

            one_to_one=one_to_one,
            nullable_one_to_one=None,

            foreign_key=foreign_key,
            nullable_foreign_key=None,

            many_to_many=[obj.to_dict() for obj in self.many_to_manys],
            another_many_to_many=self.many_to_manys,
            users=[user.pk for user in self.users]
        )

        ag_model.refresh_from_db()

        self.assertEqual(num_val, ag_model.pos_num_val)
        self.assertEqual(str_val, ag_model.non_empty_str_val)

        self.assertEqual(one_to_one, ag_model.one_to_one)
        self.assertIsNone(ag_model.nullable_one_to_one)

        self.assertEqual(foreign_key, ag_model.foreign_key)
        self.assertIsNone(ag_model.nullable_foreign_key)

        self.assert_collection_equal(self.many_to_manys, ag_model.many_to_many.all())
        self.assert_collection_equal(self.many_to_manys, ag_model.another_many_to_many.all())
        self.assertCountEqual(self.users, ag_model.users.all())

    def test_create_with_int_passed_for_to_one_relationships(self) -> None:
        one_to_one_obj = DummyForeignAutograderModel.objects.create(name='qehkfdnm')
        foreign_obj = DummyForeignAutograderModel.objects.create(name='cmnbse')

        created_with_ints = DummyAutograderModel.objects.validate_and_create(
            pos_num_val=15,
            non_empty_str_val='spam',
            read_only_field='blah',

            one_to_one=one_to_one_obj.pk,
            foreign_key=foreign_obj.pk)  # type: DummyAutograderModel

        created_with_ints.refresh_from_db()
        self.assertEqual(one_to_one_obj, created_with_ints.one_to_one)
        self.assertEqual(foreign_obj, created_with_ints.foreign_key)

    def test_create_with_dict_passed_for_to_one_relationships(self) -> None:
        one_to_one_obj = DummyForeignAutograderModel.objects.create(name='qehkfdnm')
        foreign_obj = DummyForeignAutograderModel.objects.create(name='cmnbse')

        created_with_dicts = DummyAutograderModel.objects.validate_and_create(
            pos_num_val=15,
            non_empty_str_val='spam',
            read_only_field='blah',

            one_to_one=one_to_one_obj.to_dict(),
            foreign_key=foreign_obj.to_dict())  # type: DummyAutograderModel
        created_with_dicts.refresh_from_db()
        self.assertEqual(one_to_one_obj, created_with_dicts.one_to_one)
        self.assertEqual(foreign_obj, created_with_dicts.foreign_key)

    def test_invalid_create_bad_values(self) -> None:
        with self.assertRaises(exceptions.ValidationError) as cm:
            DummyAutograderModel.objects.validate_and_create(
                pos_num_val=-42,
                non_empty_str_val='')

        self.assertIn('pos_num_val', cm.exception.message_dict)
        self.assertIn('non_empty_str_val', cm.exception.message_dict)

        self.assertFalse(DummyAutograderModel.objects.exists())


class AGModelValidateAndUpdateTestCase(UnitTestBase):
    def setUp(self) -> None:
        super().setUp()

        self.ag_model = DummyAutograderModel.objects.validate_and_create(
            pos_num_val=15,
            non_empty_str_val='spam',
            read_only_field='blah',

            one_to_one=DummyForeignAutograderModel.objects.create(name='qehkfdnm'),
            foreign_key=DummyForeignAutograderModel.objects.create(name='cmnbse'),
            many_to_many=[DummyToManyModel.objects.create(name='waaaluigi')])

        self.assertEqual(1, self.ag_model.many_to_many.count())

    def test_valid_update(self) -> None:
        new_num = self.ag_model.pos_num_val + 1
        new_str = self.ag_model.non_empty_str_val + 'aksdjhflaksdf'

        enum_field = 'egg'

        one_to_one = DummyForeignAutograderModel.objects.create(name='akjdnkajhsdf')
        foreign_key = DummyForeignAutograderModel.objects.create(name='qbdbfakdfl')

        nullable_one_to_one = DummyForeignAutograderModel.objects.create(name='akjdnkajhsdf')
        nullable_foreign_key = DummyForeignAutograderModel.objects.create(name='qbdbfakdfl')

        many_to_manys = [
            DummyToManyModel.objects.create(name='wee{}'.format(i)) for i in range(3)]
        users = [User.objects.create(username='usr{}'.format(i)) for i in range(2)]

        self.ag_model.validate_and_update(
            pos_num_val=new_num,
            non_empty_str_val=new_str,

            enum_field=enum_field,

            one_to_one=one_to_one,
            foreign_key=foreign_key,
            nullable_one_to_one=nullable_one_to_one,
            nullable_foreign_key=nullable_foreign_key,
            many_to_many=[obj.to_dict() for obj in many_to_manys],
            another_many_to_many=many_to_manys,
            users=users)

        self.ag_model.refresh_from_db()

        self.assertEqual(new_num, self.ag_model.pos_num_val)
        self.assertEqual(new_str, self.ag_model.non_empty_str_val)
        self.assertEqual(AnEnum.egg, self.ag_model.enum_field)

        self.assertEqual(one_to_one, self.ag_model.one_to_one)
        self.assertEqual(nullable_one_to_one, self.ag_model.nullable_one_to_one)

        self.assertEqual(foreign_key, self.ag_model.foreign_key)
        self.assertEqual(nullable_foreign_key, self.ag_model.nullable_foreign_key)

        self.assert_collection_equal(many_to_manys, self.ag_model.many_to_many.all())
        self.assert_collection_equal(many_to_manys, self.ag_model.another_many_to_many.all())
        self.assertCountEqual(users, self.ag_model.users.all())

        second_new_num = new_num + 1
        self.ag_model.validate_and_update(
            pos_num_val=second_new_num,
            nullable_one_to_one=None,
            nullable_foreign_key=None,
            many_to_many=[])
        self.ag_model.refresh_from_db()
        self.assertEqual(second_new_num, self.ag_model.pos_num_val)
        self.assertIsNone(self.ag_model.nullable_one_to_one)
        self.assertIsNone(self.ag_model.nullable_foreign_key)
        self.assert_collection_equal([], self.ag_model.many_to_many.all())

    def test_update_with_int_passed_for_to_one_relationships(self) -> None:
        one_to_one_obj = DummyForeignAutograderModel.objects.create(name='qehkfdnm')
        foreign_obj = DummyForeignAutograderModel.objects.create(name='cmnbse')

        obj = DummyAutograderModel.objects.validate_and_create(
            pos_num_val=15,
            non_empty_str_val='spam',
            read_only_field='blah',

            one_to_one=one_to_one_obj,
            foreign_key=foreign_obj)  # type: DummyAutograderModel

        obj.refresh_from_db()

        new_one_to_one_obj = DummyForeignAutograderModel.objects.create(name='oiuspoifdfgu')
        new_foreign_obj = DummyForeignAutograderModel.objects.create(name='sdfkgh')

        # Update -to-one relationships with pks
        obj.validate_and_update(one_to_one=new_one_to_one_obj.pk,
                                foreign_key=new_foreign_obj.pk)
        obj.refresh_from_db()

        self.assertEqual(new_one_to_one_obj, obj.one_to_one)
        self.assertEqual(new_foreign_obj, obj.foreign_key)

    def test_update_with_dict_passed_for_to_one_relationships(self) -> None:
        one_to_one_obj = DummyForeignAutograderModel.objects.create(name='qehkfdnm')
        foreign_obj = DummyForeignAutograderModel.objects.create(name='cmnbse')

        obj = DummyAutograderModel.objects.validate_and_create(
            pos_num_val=15,
            non_empty_str_val='spam',
            read_only_field='blah',

            one_to_one=one_to_one_obj,
            foreign_key=foreign_obj)  # type: DummyAutograderModel

        obj.refresh_from_db()

        new_one_to_one_obj = DummyForeignAutograderModel.objects.create(name='oiuspoifdfgu')
        new_foreign_obj = DummyForeignAutograderModel.objects.create(name='sdfkgh')

        # Update -to-one relationships with dicts
        obj.validate_and_update(one_to_one=new_one_to_one_obj.to_dict(),
                                foreign_key=new_foreign_obj.to_dict())
        obj.refresh_from_db()

        self.assertEqual(new_one_to_one_obj, obj.one_to_one)
        self.assertEqual(new_foreign_obj, obj.foreign_key)

    def test_invalid_update_bad_values(self) -> None:
        old_vals = self.ag_model.to_dict()

        with self.assertRaises(exceptions.ValidationError) as cm:
            self.ag_model.validate_and_update(pos_num_val=-42,
                                              non_empty_str_val='')

        self.assertIn('pos_num_val', cm.exception.message_dict)
        self.assertIn('non_empty_str_val', cm.exception.message_dict)

        self.ag_model.refresh_from_db()
        self.assert_dict_contents_equal(old_vals, self.ag_model.to_dict())

    def test_invalid_update_nonexistant_field(self) -> None:
        with self.assertRaises(exceptions.ValidationError) as cm:
            self.ag_model.validate_and_update(not_a_field_name='spam')

        self.assertIn(
            'not_a_field_name',
            cm.exception.message_dict[AutograderModel.INVALID_FIELD_NAMES_KEY])

    def test_invalid_update_non_editable_field(self) -> None:
        with self.assertRaises(exceptions.ValidationError) as cm:
            self.ag_model.validate_and_update(read_only_field='steve')

        self.assertIn('non_editable_fields', cm.exception.message_dict)
        self.assertIn('read_only_field',
                      cm.exception.message_dict['non_editable_fields'])


class CreateAGModelWithSerializableFieldTest(UnitTestBase):
    def test_to_dict(self) -> None:
        data = {
            'num': 42,
            'string': 'nsroitenarositean',
            'an_enum': AnEnum.spam
        }

        obj = AGModelWithSerializableField.objects.validate_and_create(
            serializable=data,
            # Make sure it handles explicitly passing in None
            nullable_serializable=None
        )

        expected: Dict[str, Any] = {
            'serializable': copy.copy(data),
            'nullable_serializable': None
        }
        expected['serializable']['an_enum'] = expected['serializable']['an_enum'].value
        expected['serializable']['has_default'] = DictSerializableClass.has_default_default_val

        # Check serialization before and after refreshing.
        self.assertEqual(expected, obj.to_dict())
        obj.refresh_from_db()
        self.assertEqual(expected, obj.to_dict())

    def test_create_with_dict_param_nullable_is_null(self) -> None:
        data = {
            'num': 24,
            'string': 'nxcvn',
            'an_enum': AnEnum.egg.value
        }

        obj = AGModelWithSerializableField.objects.validate_and_create(
            serializable=data,
            nullable_serializable=None
        )

        obj.refresh_from_db()

        self.assertEqual(data['num'], obj.serializable.num)
        self.assertEqual(data['string'], obj.serializable.string)
        self.assertEqual(AnEnum.egg, obj.serializable.an_enum)

        self.assertIsNone(obj.nullable_serializable)

    def test_create_with_dict_param_nullable_is_non_null(self) -> None:
        data = {
            'num': 24,
            'string': 'nxcvn',
            'an_enum': AnEnum.egg.value
        }

        obj = AGModelWithSerializableField.objects.validate_and_create(
            serializable=data,
            nullable_serializable=data
        )

        obj.refresh_from_db()

        self.assertEqual(data['num'], obj.serializable.num)
        self.assertEqual(data['string'], obj.serializable.string)
        self.assertEqual(AnEnum.egg, obj.serializable.an_enum)

        self.assertEqual(data['num'], obj.nullable_serializable.num)
        self.assertEqual(data['string'], obj.nullable_serializable.string)
        self.assertEqual(AnEnum.egg, obj.nullable_serializable.an_enum)

    def test_create_with_class_param_nullable_is_null(self) -> None:
        serializable = DictSerializableClass(
            num=67,
            string='qpfwp',
            an_enum=AnEnum.egg
        )

        obj = AGModelWithSerializableField.objects.validate_and_create(
            serializable=serializable,
            nullable_serializable=None
        )

        obj.refresh_from_db()

        self.assertEqual(serializable.num, obj.serializable.num)
        self.assertEqual(serializable.string, obj.serializable.string)
        self.assertEqual(serializable.an_enum, obj.serializable.an_enum)

        self.assertIsNone(obj.nullable_serializable)

    def test_create_with_class_param_nullable_is_non_null(self) -> None:
        serializable = DictSerializableClass(
            num=67,
            string='qpfwp',
            an_enum=AnEnum.egg
        )

        obj = AGModelWithSerializableField.objects.validate_and_create(
            serializable=serializable,
            nullable_serializable=serializable
        )

        obj.refresh_from_db()

        self.assertEqual(serializable.num, obj.serializable.num)
        self.assertEqual(serializable.string, obj.serializable.string)
        self.assertEqual(serializable.an_enum, obj.serializable.an_enum)

        self.assertEqual(serializable.num, obj.nullable_serializable.num)
        self.assertEqual(serializable.string, obj.nullable_serializable.string)
        self.assertEqual(serializable.an_enum, obj.nullable_serializable.an_enum)

    def test_create_error_extra_field(self) -> None:
        data = {
            'num': 19,
            'string': 'jaeija',
            'an_enum': AnEnum.spam,
            'extra': 45
        }

        with self.assertRaises(exceptions.ValidationError) as cm:
            AGModelWithSerializableField.objects.validate_and_create(serializable=data)

        self.assertIn('serializable', cm.exception.message_dict)
        self.assertIn('Extra fields:', cm.exception.message_dict['serializable'][0])

    def test_error_missing_required_field(self) -> None:
        with self.assertRaises(exceptions.ValidationError) as cm:
            AGModelWithSerializableField.objects.validate_and_create(
                serializable={
                    'num': 42,
                    'an_enum': AnEnum.spam
                }
            )

        self.assertIn('string', cm.exception.message_dict['serializable'][0])

        with self.assertRaises(exceptions.ValidationError) as cm:
            AGModelWithSerializableField.objects.validate_and_create(
                nullable_serializable={
                    'num': 42,
                    'string': 'spam'
                }
            )

        self.assertIn('an_enum', cm.exception.message_dict['nullable_serializable'][0])

    def test_create_error_wrong_type(self) -> None:
        data = {
            'num': '34',
            'string': 'aeiai',
            'an_enum': AnEnum.egg,
        }

        with self.assertRaises(exceptions.ValidationError) as cm:
            AGModelWithSerializableField.objects.validate_and_create(serializable=data)

        self.assertIn('serializable', cm.exception.message_dict)
        self.assertIn('num:', cm.exception.message_dict['serializable'][0])

    def test_create_error_bad_enum_value(self) -> None:
        data = {
            'num': 23,
            'string': 'sss',
            'an_enum': 'not_a_value',
        }

        with self.assertRaises(exceptions.ValidationError) as cm:
            AGModelWithSerializableField.objects.validate_and_create(serializable=data)

        self.assertIn('serializable', cm.exception.message_dict)
        self.assertIn('an_enum:', cm.exception.message_dict['serializable'][0])

    def test_non_nullable_is_null(self) -> None:
        with self.assertRaises(exceptions.ValidationError) as cm:
            AGModelWithSerializableField.objects.validate_and_create(serializable=None)

        self.assertIn('serializable', cm.exception.message_dict)


class UpdateAGModelWithSerializableFieldTest(UnitTestBase):
    def setUp(self) -> None:
        super().setUp()

        self.obj: AGModelWithSerializableField = (
            AGModelWithSerializableField.objects.validate_and_create(
                serializable={
                    'num': 90,
                    'string': 'wnifetasor',
                    'an_enum': AnEnum.egg
                }
            )
        )

    def test_full_update_with_dict_param_nullable_is_null(self) -> None:
        self.assertIsNone(self.obj.nullable_serializable)

        new_data = {
            'num': 76,
            'string': 'waaaaluigi',
            'an_enum': AnEnum.spam.value,
        }

        self.obj.validate_and_update(serializable=new_data, nullable_serializable=new_data)

        self.obj.refresh_from_db()

        self.assertEqual(new_data['num'], self.obj.serializable.num)
        self.assertEqual(new_data['string'], self.obj.serializable.string)
        self.assertEqual(AnEnum.spam, self.obj.serializable.an_enum)

        self.assertEqual(new_data['num'], self.obj.nullable_serializable.num)
        self.assertEqual(new_data['string'], self.obj.nullable_serializable.string)
        self.assertEqual(AnEnum.spam, self.obj.nullable_serializable.an_enum)

    def test_full_update_with_dict_param_nullable_is_non_null(self) -> None:
        self.obj.nullable_serializable = self.obj.serializable
        self.obj.save()

        new_data = {
            'num': 76,
            'string': 'waaaaluigi',
            'an_enum': AnEnum.spam.value,
        }

        self.obj.validate_and_update(serializable=new_data, nullable_serializable=new_data)

        self.obj.refresh_from_db()

        self.assertEqual(new_data['num'], self.obj.serializable.num)
        self.assertEqual(new_data['string'], self.obj.serializable.string)
        self.assertEqual(AnEnum.spam, self.obj.serializable.an_enum)

        self.assertEqual(new_data['num'], self.obj.nullable_serializable.num)
        self.assertEqual(new_data['string'], self.obj.nullable_serializable.string)
        self.assertEqual(AnEnum.spam, self.obj.nullable_serializable.an_enum)

    def test_partial_update_with_dict_param_nullable_is_null(self) -> None:
        self.assertIsNone(self.obj.nullable_serializable)

        original_num = self.obj.serializable.num
        original_an_enum = self.obj.serializable.an_enum
        original_string = self.obj.serializable.string
        new_data = {
            'string': 'stove',
        }

        self.obj.validate_and_update(serializable=new_data,
                                     nullable_serializable=self.obj.serializable.to_dict())
        self.obj.refresh_from_db()

        self.assertEqual(new_data['string'], self.obj.serializable.string)

        self.assertEqual(original_num, self.obj.serializable.num)
        self.assertEqual(original_an_enum, self.obj.serializable.an_enum)

        self.assertEqual(original_num, self.obj.nullable_serializable.num)
        self.assertEqual(original_an_enum, self.obj.nullable_serializable.an_enum)
        self.assertEqual(original_string, self.obj.nullable_serializable.string)
        self.assertEqual(DictSerializableClass.has_default_default_val,
                         self.obj.nullable_serializable.has_default)

    def test_error_nullable_is_null_partial_update_with_dict_missing_required_field(self) -> None:
        self.assertIsNone(self.obj.nullable_serializable)

        with self.assertRaises(exceptions.ValidationError) as cm:
            self.obj.validate_and_update(
                nullable_serializable={
                    'num': 42,
                    'string': 'spam'
                }
            )

        self.assertIn('an_enum', cm.exception.message_dict['nullable_serializable'][0])

    def test_partial_update_with_dict_param_nullable_is_non_null(self) -> None:
        self.obj.nullable_serializable = self.obj.serializable.to_dict()
        self.obj.save()

        original_num = self.obj.serializable.num
        original_an_enum = self.obj.serializable.an_enum
        new_data = {
            'string': 'stove',
        }

        new_nullable_string = 'cheese'

        self.obj.validate_and_update(serializable=new_data,
                                     nullable_serializable={'string': new_nullable_string})
        self.obj.refresh_from_db()

        self.assertEqual(new_data['string'], self.obj.serializable.string)

        self.assertEqual(original_num, self.obj.serializable.num)
        self.assertEqual(original_an_enum, self.obj.serializable.an_enum)

        self.assertEqual(new_nullable_string, self.obj.nullable_serializable.string)
        self.assertEqual(original_num, self.obj.nullable_serializable.num)
        self.assertEqual(original_an_enum, self.obj.nullable_serializable.an_enum)

    def test_update_with_class_param(self) -> None:
        new_data = copy.deepcopy(self.obj.serializable)
        new_data.num = 892

        self.obj.validate_and_update(serializable=new_data)
        self.obj.refresh_from_db()

        self.assertEqual(new_data.num, self.obj.serializable.num)
        self.assertEqual(new_data.string, self.obj.serializable.string)
        self.assertEqual(new_data.an_enum, self.obj.serializable.an_enum)

    def test_update_error_extra_field(self) -> None:
        data = {
            'extra': 45
        }

        with self.assertRaises(exceptions.ValidationError) as cm:
            self.obj.validate_and_update(serializable=data)

        self.assertIn('serializable', cm.exception.message_dict)
        self.assertIn('Extra fields:', cm.exception.message_dict['serializable'][0])

    def test_update_error_wrong_type(self) -> None:
        data = {
            'string': 42,
        }

        with self.assertRaises(exceptions.ValidationError) as cm:
            self.obj.validate_and_update(serializable=data)

        self.assertIn('serializable', cm.exception.message_dict)
        self.assertIn('string:', cm.exception.message_dict['serializable'][0])

    def test_update_error_bad_enum_value(self) -> None:
        data = {

            'an_enum': 'not_a_value',
        }

        with self.assertRaises(exceptions.ValidationError) as cm:
            self.obj.validate_and_update(serializable=data)

        self.assertIn('serializable', cm.exception.message_dict)
        self.assertIn('an_enum:', cm.exception.message_dict['serializable'][0])


class _MyEnum(enum.Enum):
    one = 'one'
    two = 'two'


def _make_min_value_validator(min_value: int) -> Callable[[object], None]:
    def validator(value: object) -> None:
        assert isinstance(value, int)
        if value < min_value:
            raise exceptions.ValidationError(f'Must be >= {min_value}')

    return validator


def _make_max_value_validator(max_value: int) -> Callable[[object], None]:
    def validator(value: object) -> None:
        assert isinstance(value, int)
        if value > max_value:
            raise exceptions.ValidationError(f'Must be <= {max_value}')

    return validator


class _SerializableClass(DictSerializable):
    def __init__(self, required_int: int,
                 optional_bool: bool = True,
                 my_enum: _MyEnum = _MyEnum.one,
                 less_than: int = 0,
                 greater_than: int = 5):
        self.required_int = required_int
        self.optional_bool = optional_bool
        self.my_enum = my_enum
        self.less_than = less_than
        self.greater_than = greater_than

    FIELD_VALIDATORS = {
        'required_int': [_make_min_value_validator(0), _make_max_value_validator(10)]
    }

    def validate(self) -> None:
        if self.less_than >= self.greater_than:
            raise exceptions.ValidationError(
                '"less_than" must be greater than "greater_than"')


class DictSerializableMixinTestCase(SimpleTestCase):
    def test_valid_from_dict(self) -> None:
        obj = _SerializableClass.from_dict({'required_int': 5})
        self.assertEqual(5, obj.required_int)
        self.assertTrue(obj.optional_bool)
        self.assertEqual(_MyEnum.one, obj.my_enum)

        obj = _SerializableClass.from_dict({
            'required_int': 6,
            'optional_bool': False,
            'my_enum': _MyEnum.two,
            'less_than': 2,
            'greater_than': 4
        })
        self.assertEqual(6, obj.required_int)
        self.assertFalse(obj.optional_bool)
        self.assertEqual(_MyEnum.two, obj.my_enum)
        self.assertEqual(obj.less_than, 2)
        self.assertEqual(obj.greater_than, 4)

    def test_valid_update(self) -> None:
        obj = _SerializableClass.from_dict({'required_int': 5})
        self.assertEqual(5, obj.required_int)
        self.assertTrue(obj.optional_bool)
        self.assertEqual(_MyEnum.one, obj.my_enum)

        obj.update({'optional_bool': False})
        self.assertFalse(obj.optional_bool)

        obj.update({
            'required_int': 6,
            'optional_bool': False,
            'my_enum': _MyEnum.two,
            'less_than': 2,
            'greater_than': 4
        })
        self.assertEqual(6, obj.required_int)
        self.assertFalse(obj.optional_bool)
        self.assertEqual(_MyEnum.two, obj.my_enum)
        self.assertEqual(obj.less_than, 2)
        self.assertEqual(obj.greater_than, 4)

    def test_error_missing_required_field(self) -> None:
        with self.assertRaises(exceptions.ValidationError) as cm:
            _SerializableClass.from_dict({})

        self.assertIn('required_int', cm.exception.message)

    def test_extra_field_present(self) -> None:
        with self.assertRaises(exceptions.ValidationError) as cm:
            _SerializableClass.from_dict({'required_int': 5, 'extra_field': 42})

        self.assertIn('extra_field', cm.exception.message)

        obj = _SerializableClass.from_dict({'required_int': 5})
        with self.assertRaises(exceptions.ValidationError) as cm:
            obj.update({'required_int': 7, 'extra_field': 42})

        self.assertIn('extra_field', cm.exception.message)
        self.assertEqual(5, obj.required_int)

    def test_error_bad_field_type(self) -> None:
        with self.assertRaises(exceptions.ValidationError) as cm:
            _SerializableClass.from_dict({'required_int': 'spam'})

        self.assertIn('required_int', cm.exception.message)

        obj = _SerializableClass.from_dict({'required_int': 5})
        with self.assertRaises(exceptions.ValidationError) as cm:
            obj.update({'optional_bool': 'egg'})

        self.assertIn('optional_bool', cm.exception.message)

    def test_error_bad_field_enum_type(self) -> None:
        with self.assertRaises(exceptions.ValidationError) as cm:
            _SerializableClass.from_dict({'required_int': 5, 'my_enum': 'nope'})

        self.assertIn('my_enum', cm.exception.message)

        obj = _SerializableClass.from_dict({'required_int': 5})
        with self.assertRaises(exceptions.ValidationError) as cm:
            obj.update({'my_enum': 'noooope'})

        self.assertIn('my_enum', cm.exception.message)

    def test_error_custom_field_validation_failure(self) -> None:
        with self.assertRaises(exceptions.ValidationError) as cm:
            _SerializableClass.from_dict({'required_int': -1})

        self.assertIn('required_int', cm.exception.message)

        with self.assertRaises(exceptions.ValidationError) as cm:
            _SerializableClass.from_dict({'required_int': 11})

        self.assertIn('required_int', cm.exception.message)

        obj = _SerializableClass.from_dict({'required_int': 5})
        with self.assertRaises(exceptions.ValidationError) as cm:
            obj.update({'required_int': -1})

        self.assertIn('required_int', cm.exception.message)
        self.assertEqual(5, obj.required_int)

        with self.assertRaises(exceptions.ValidationError) as cm:
            obj.update({'required_int': 11})

        self.assertIn('required_int', cm.exception.message)
        self.assertEqual(5, obj.required_int)

    def test_error_custom_object_validation_failure(self) -> None:
        with self.assertRaises(exceptions.ValidationError) as cm:
            _SerializableClass.from_dict({
                'required_int': 4,
                'less_than': 5,
                'greater_than': 4
            })

        self.assertIn('less_than', cm.exception.message)
        self.assertIn('greater_than', cm.exception.message)

        obj = _SerializableClass.from_dict({'required_int': 2})
        with self.assertRaises(exceptions.ValidationError) as cm:
            obj.update({'required_int': 3, 'less_than': 5, 'greater_than': 4})

        self.assertIn('less_than', cm.exception.message)
        self.assertIn('greater_than', cm.exception.message)

        self.assertEqual(0, obj.less_than)
        self.assertEqual(5, obj.greater_than)
        self.assertEqual(2, obj.required_int)

    def test_allowed_fields_excludes_self(self) -> None:
        with self.assertRaises(exceptions.ValidationError) as cm:
            _SerializableClass.from_dict({'required_int': 2, 'self': None})

        self.assertIn('self', cm.exception.message)
        self.assertIn('extra', cm.exception.message.lower())

    def test_serialize(self) -> None:
        data = {
            'required_int': 3,
            'optional_bool': True,
            'my_enum': _MyEnum.two,
            'less_than': 2,
            'greater_than': 4
        }

        serialized = copy.deepcopy(data)
        serialized['my_enum'] = _MyEnum.two.value

        obj = _SerializableClass.from_dict(data)
        self.assertEqual(serialized, obj.to_dict())

        cloned = _SerializableClass.from_dict(obj.to_dict())
        for key, value in data.items():
            self.assertEqual(value, getattr(cloned, key))
