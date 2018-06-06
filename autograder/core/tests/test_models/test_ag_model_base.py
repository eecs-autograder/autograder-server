import copy
from unittest import mock

from django.contrib.auth.models import User
from django.core import exceptions

from autograder.core.models.ag_model_base import AutograderModel
from autograder.utils.testing import UnitTestBase

from .models import (
    DummyAutograderModel, DummyForeignAutograderModel, DummyToManyModel, AnEnum,
    AGModelWithSerializableField, DictSerializableClass)


class AGModelBaseToDictTest(UnitTestBase):
    def setUp(self):
        super().setUp()

        self.maxDiff = None

        self.ag_model = DummyAutograderModel.objects.create(
            pos_num_val=15,
            non_empty_str_val='spam',
            one_to_one=DummyForeignAutograderModel.objects.create(name='akdsjhfalsd'),
            foreign_key=DummyForeignAutograderModel.objects.create(name='bekjfahsdf'),
            transparent_to_one=DummyForeignAutograderModel.objects.create(name='kadhfkasdhfl'),
            transparent_foreign_key=DummyForeignAutograderModel.objects.create(name='JHBQDFJASD'))

        self.many_to_manys = [
            DummyToManyModel.objects.create(name='wee{}'.format(i)) for i in range(3)]
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
            'enum_property': 'egg',

            'enum_field': 'spam',

            'one_to_one': self.ag_model.one_to_one.pk,
            'one_to_one_id': self.ag_model.one_to_one.pk,
            'nullable_one_to_one': None,
            'nullable_one_to_one_id': None,
            'transparent_to_one': self.ag_model.transparent_to_one.to_dict(),
            'transparent_nullable_to_one': None,

            'foreign_key': self.ag_model.foreign_key.pk,
            'foreign_key_id': self.ag_model.foreign_key.pk,
            'nullable_foreign_key': None,
            'nullable_foreign_key_id': None,
            'transparent_foreign_key': self.ag_model.transparent_foreign_key.to_dict(),
            'transparent_nullable_foreign_key': None,

            'many_to_many': [obj.pk for obj in self.many_to_manys],
            'another_many_to_many': [],

            'users': [user.pk for user in self.users]
        }
        result = self.ag_model.to_dict()
        result['users'].sort()
        print(result)
        self.assertEqual(expected, result)

        expected_one_to_many = {
            'pk': self.ag_model.foreign_key.pk,
            'name': self.ag_model.foreign_key.name,
            'rev_foreign_key': [self.ag_model.pk]
        }
        self.assertEqual(expected_one_to_many, self.ag_model.foreign_key.to_dict())

    def test_to_one_and_to_many_in_serialize_related(self):
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
                'transparent_to_one': self.ag_model.transparent_to_one.to_dict(),
                'transparent_nullable_to_one': None,

                'foreign_key': self.ag_model.foreign_key.to_dict(),
                'foreign_key_id': self.ag_model.foreign_key.pk,
                'nullable_foreign_key': None,
                'nullable_foreign_key_id': None,
                'transparent_foreign_key': self.ag_model.transparent_foreign_key.to_dict(),
                'transparent_nullable_foreign_key': None,

                'many_to_many': [obj.to_dict() for obj in self.many_to_manys],
                'another_many_to_many': [],

                'users': [user.pk for user in self.users]
            }

            result = self.ag_model.to_dict()
            result['users'].sort()

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

    def test_empty_to_many_serialized_correctly(self):
        self.ag_model.many_to_many.clear()
        self.assertSequenceEqual([], self.ag_model.to_dict()['many_to_many'])


class AGModelValidateAndCreateTestCase(UnitTestBase):
    def setUp(self):
        super().setUp()

        self.many_to_manys = [
            DummyToManyModel.objects.create(name='wee{}'.format(i)) for i in range(3)]
        self.users = [
            User.objects.create(username='usr{}'.format(i)) for i in range(2)]

    def test_valid_create(self):
        num_val = 827349
        str_val = 'badsvihajhfs'

        one_to_one = DummyForeignAutograderModel.objects.create(name='akjdnkajhsdf')
        foreign_key = DummyForeignAutograderModel.objects.create(name='qbdbfakdfl')

        transparent_to_one_name = 'qiwefhsd'
        transparent_foreign_key_name = 'aksjdhfakj'

        ag_model = DummyAutograderModel.objects.validate_and_create(
            pos_num_val=num_val,
            non_empty_str_val=str_val,

            one_to_one=one_to_one,
            nullable_one_to_one=None,
            transparent_to_one={'name': transparent_to_one_name},

            foreign_key=foreign_key,
            nullable_foreign_key=None,
            transparent_foreign_key={'name': transparent_foreign_key_name},

            many_to_many=[obj.to_dict() for obj in self.many_to_manys],
            another_many_to_many=self.many_to_manys,
            users=[user.pk for user in self.users]
        )

        ag_model.refresh_from_db()

        self.assertEqual(num_val, ag_model.pos_num_val)
        self.assertEqual(str_val, ag_model.non_empty_str_val)

        self.assertEqual(one_to_one, ag_model.one_to_one)
        self.assertIsNone(ag_model.nullable_one_to_one)
        self.assertEqual(transparent_to_one_name, ag_model.transparent_to_one.name)
        self.assertIsNone(ag_model.transparent_nullable_to_one)

        self.assertEqual(foreign_key, ag_model.foreign_key)
        self.assertIsNone(ag_model.nullable_foreign_key)
        self.assertEqual(transparent_foreign_key_name, ag_model.transparent_foreign_key.name)
        self.assertIsNone(ag_model.transparent_nullable_foreign_key)

        self.assertSequenceEqual(self.many_to_manys, ag_model.many_to_many.all())
        self.assertSequenceEqual(self.many_to_manys, ag_model.another_many_to_many.all())
        self.assertCountEqual(self.users, ag_model.users.all())

    def test_create_with_int_passed_for_to_one_relationships(self):
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

    def test_create_with_dict_passed_for_to_one_relationships(self):
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

    def test_invalid_create_bad_values(self):
        with self.assertRaises(exceptions.ValidationError) as cm:
            DummyAutograderModel.objects.validate_and_create(
                pos_num_val=-42,
                non_empty_str_val='')

        self.assertIn('pos_num_val', cm.exception.message_dict)
        self.assertIn('non_empty_str_val', cm.exception.message_dict)

        self.assertFalse(DummyAutograderModel.objects.exists())


class AGModelValidateAndUpdateTestCase(UnitTestBase):
    def setUp(self):
        super().setUp()

        self.ag_model = DummyAutograderModel.objects.validate_and_create(
            pos_num_val=15,
            non_empty_str_val='spam',
            read_only_field='blah',

            one_to_one=DummyForeignAutograderModel.objects.create(name='qehkfdnm'),
            foreign_key=DummyForeignAutograderModel.objects.create(name='cmnbse'),
            many_to_many=[DummyToManyModel.objects.create(name='waaaluigi')])

        self.assertEqual(1, self.ag_model.many_to_many.count())

    def test_valid_update(self):
        new_num = self.ag_model.pos_num_val + 1
        new_str = self.ag_model.non_empty_str_val + 'aksdjhflaksdf'

        enum_field = 'egg'

        one_to_one = DummyForeignAutograderModel.objects.create(name='akjdnkajhsdf')
        foreign_key = DummyForeignAutograderModel.objects.create(name='qbdbfakdfl')

        orig_transparent_to_one = self.ag_model.transparent_to_one
        transparent_to_one_name = 'qiwefhsd'
        orig_transparent_foreign_key = self.ag_model.transparent_foreign_key
        transparent_foreign_key_name = 'aksjdhfakj'

        many_to_manys = [
            DummyToManyModel.objects.create(name='wee{}'.format(i)) for i in range(3)]
        users = [User.objects.create(username='usr{}'.format(i)) for i in range(2)]

        self.ag_model.validate_and_update(
            pos_num_val=new_num,
            non_empty_str_val=new_str,

            enum_field=enum_field,

            one_to_one=one_to_one,
            foreign_key=foreign_key,
            transparent_to_one={'name': transparent_to_one_name},
            transparent_foreign_key={'name': transparent_foreign_key_name},
            many_to_many=[obj.to_dict() for obj in many_to_manys],
            another_many_to_many=many_to_manys,
            users=users)

        self.ag_model.refresh_from_db()

        self.assertEqual(new_num, self.ag_model.pos_num_val)
        self.assertEqual(new_str, self.ag_model.non_empty_str_val)
        self.assertEqual(AnEnum.egg, self.ag_model.enum_field)

        self.assertEqual(one_to_one, self.ag_model.one_to_one)
        self.assertIsNone(self.ag_model.nullable_one_to_one)
        # Make sure we updated the transparent object rather than replacing it
        # with a new one.
        self.assertEqual(orig_transparent_to_one, self.ag_model.transparent_to_one)
        self.assertEqual(transparent_to_one_name, self.ag_model.transparent_to_one.name)

        self.assertEqual(foreign_key, self.ag_model.foreign_key)
        self.assertIsNone(self.ag_model.nullable_foreign_key)
        self.assertEqual(orig_transparent_foreign_key, self.ag_model.transparent_foreign_key)
        self.assertEqual(transparent_foreign_key_name, self.ag_model.transparent_foreign_key.name)

        self.assertSequenceEqual(many_to_manys, self.ag_model.many_to_many.all())
        self.assertSequenceEqual(many_to_manys, self.ag_model.another_many_to_many.all())
        self.assertCountEqual(users, self.ag_model.users.all())

        second_new_num = new_num + 1
        self.ag_model.validate_and_update(
            pos_num_val=second_new_num,
            nullable_foreign_key=None,
            many_to_many=[])
        self.ag_model.refresh_from_db()
        self.assertEqual(second_new_num, self.ag_model.pos_num_val)
        self.assertIsNone(self.ag_model.nullable_foreign_key)
        self.assertSequenceEqual([], self.ag_model.many_to_many.all())

    def test_update_with_int_passed_for_to_one_relationships(self):
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

    def test_update_with_dict_passed_for_to_one_relationships(self):
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

    def test_update_nullable_to_one_from_null_to_value(self):
        one_to_one_obj = DummyForeignAutograderModel.objects.create(name='qehkfdnm')
        foreign_obj = DummyForeignAutograderModel.objects.create(name='cmnbse')

        obj = DummyAutograderModel.objects.validate_and_create(
            pos_num_val=15,
            non_empty_str_val='spam',
            read_only_field='blah',

            one_to_one=one_to_one_obj,
            foreign_key=foreign_obj)  # type: DummyAutograderModel

        self.assertIsNone(obj.transparent_nullable_to_one)
        self.assertIsNone(obj.transparent_nullable_foreign_key)

        name1 = 'qewrasdfoiadsuf'
        name2 = 'avaejfa'
        obj.validate_and_update(
            transparent_nullable_to_one={'name': name1},
            transparent_nullable_foreign_key={'name': name2})

        self.assertEqual(name1, obj.transparent_nullable_to_one.name)
        self.assertEqual(name2, obj.transparent_nullable_foreign_key.name)

    def test_update_nullable_to_one_from_value_to_null_value_deleted(self):
        one_to_one_obj = DummyForeignAutograderModel.objects.create(name='qehkfdnm')
        foreign_obj = DummyForeignAutograderModel.objects.create(name='cmnbse')

        obj = DummyAutograderModel.objects.validate_and_create(
            pos_num_val=15,
            non_empty_str_val='spam',
            read_only_field='blah',

            one_to_one=one_to_one_obj,
            foreign_key=foreign_obj,
            transparent_nullable_to_one={'name': 'asdfnaoiwej'},
            transparent_nullable_foreign_key={'name': 'skdfjs'})  # type: DummyAutograderModel

        num_foreign_objs = DummyForeignAutograderModel.objects.count()

        obj.validate_and_update(
            transparent_nullable_to_one=None,
            transparent_nullable_foreign_key=None)

        obj.refresh_from_db()

        self.assertIsNone(obj.transparent_nullable_to_one)
        self.assertIsNone(obj.transparent_nullable_foreign_key)

        self.assertEqual(num_foreign_objs - 2, DummyForeignAutograderModel.objects.count())

    def test_invalid_update_bad_values(self):
        old_vals = self.ag_model.to_dict()

        with self.assertRaises(exceptions.ValidationError) as cm:
            self.ag_model.validate_and_update(pos_num_val=-42,
                                              non_empty_str_val='')

        self.assertIn('pos_num_val', cm.exception.message_dict)
        self.assertIn('non_empty_str_val', cm.exception.message_dict)

        self.ag_model.refresh_from_db()
        self.assert_dict_contents_equal(old_vals, self.ag_model.to_dict())

    def test_invalid_update_nonexistant_field(self):
        with self.assertRaises(exceptions.ValidationError) as cm:
            self.ag_model.validate_and_update(not_a_field_name='spam')

        self.assertIn(
            'not_a_field_name',
            cm.exception.message_dict[AutograderModel.INVALID_FIELD_NAMES_KEY])

    def test_invalid_update_non_editable_field(self):
        with self.assertRaises(exceptions.ValidationError) as cm:
            self.ag_model.validate_and_update(read_only_field='steve')

        self.assertIn('non_editable_fields', cm.exception.message_dict)
        self.assertIn('read_only_field',
                      cm.exception.message_dict['non_editable_fields'])


class CreateAGModelWithSerializableFieldTest(UnitTestBase):
    def test_to_dict(self):
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

        expected = {
            'serializable': copy.copy(data),
            'nullable_serializable': None
        }
        expected['serializable']['an_enum'] = expected['serializable']['an_enum'].value
        expected['serializable']['has_default'] = DictSerializableClass.has_default_default_val

        # Check serialization before and after refreshing.
        self.assertEqual(expected, obj.to_dict())
        obj.refresh_from_db()
        self.assertEqual(expected, obj.to_dict())

    def test_create_with_dict_param(self):
        data = {
            'num': 24,
            'string': 'nxcvn',
            'an_enum': AnEnum.egg.value
        }

        obj = AGModelWithSerializableField.objects.validate_and_create(
            serializable=data
        )

        obj.refresh_from_db()

        self.assertEqual(data['num'], obj.serializable.num)
        self.assertEqual(data['string'], obj.serializable.string)
        self.assertEqual(AnEnum.egg, obj.serializable.an_enum)

    def test_create_with_class_param(self):
        serializable = DictSerializableClass(
            num=67,
            string='qpfwp',
            an_enum=AnEnum.egg
        )

        obj = AGModelWithSerializableField.objects.validate_and_create(
            serializable=serializable
        )

        obj.refresh_from_db()

        self.assertEqual(serializable.num, obj.serializable.num)
        self.assertEqual(serializable.string, obj.serializable.string)
        self.assertEqual(serializable.an_enum, obj.serializable.an_enum)

    def test_create_error_extra_field(self):
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

    def test_create_error_wrong_type(self):
        data = {
            'num': '34',
            'string': 'aeiai',
            'an_enum': AnEnum.egg,
        }

        with self.assertRaises(exceptions.ValidationError) as cm:
            AGModelWithSerializableField.objects.validate_and_create(serializable=data)

        self.assertIn('serializable', cm.exception.message_dict)
        self.assertIn('num:', cm.exception.message_dict['serializable'][0])

    def test_create_error_bad_enum_value(self):
        data = {
            'num': 23,
            'string': 'sss',
            'an_enum': 'not_a_value',
        }

        with self.assertRaises(exceptions.ValidationError) as cm:
            AGModelWithSerializableField.objects.validate_and_create(serializable=data)

        self.assertIn('serializable', cm.exception.message_dict)
        self.assertIn('an_enum:', cm.exception.message_dict['serializable'][0])

    def test_non_nullable_is_null(self):
        with self.assertRaises(exceptions.ValidationError) as cm:
            AGModelWithSerializableField.objects.validate_and_create(serializable=None)

        self.assertIn('serializable', cm.exception.message_dict)


class UpdateAGModelWithSerializableFieldTest(UnitTestBase):
    def setUp(self):
        super().setUp()

        self.obj = AGModelWithSerializableField.objects.validate_and_create(
            serializable={
                'num': 90,
                'string': 'wnifetasor',
                'an_enum': AnEnum.egg
            }
        )

    def test_full_update_with_dict_param(self):
        new_data = {
            'num': 76,
            'string': 'waaaaluigi',
            'an_enum': AnEnum.spam.value,
        }

        self.obj.validate_and_update(serializable=new_data)

        self.obj.refresh_from_db()

        self.assertEqual(new_data['num'], self.obj.serializable.num)
        self.assertEqual(new_data['string'], self.obj.serializable.string)
        self.assertEqual(AnEnum.spam, self.obj.serializable.an_enum)

    def test_partial_update_with_dict_param(self):
        original_num = self.obj.serializable.num
        original_an_enum = self.obj.serializable.an_enum
        new_data = {
            'string': 'stove',
        }

        self.obj.validate_and_update(serializable=new_data)
        self.obj.refresh_from_db()

        self.assertEqual(new_data['string'], self.obj.serializable.string)

        self.assertEqual(original_num, self.obj.serializable.num)
        self.assertEqual(original_an_enum, self.obj.serializable.an_enum)

    def test_update_with_class_param(self):
        new_data = copy.deepcopy(self.obj.serializable)
        new_data.num = 892

        self.obj.validate_and_update(serializable=new_data)
        self.obj.refresh_from_db()

        self.assertEqual(new_data.num, self.obj.serializable.num)
        self.assertEqual(new_data.string, self.obj.serializable.string)
        self.assertEqual(new_data.an_enum, self.obj.serializable.an_enum)

    def test_update_error_extra_field(self):
        data = {
            'extra': 45
        }

        with self.assertRaises(exceptions.ValidationError) as cm:
            self.obj.validate_and_update(serializable=data)

        self.assertIn('serializable', cm.exception.message_dict)
        self.assertIn('Extra fields:', cm.exception.message_dict['serializable'][0])

    def test_update_error_wrong_type(self):
        data = {
            'string': 42,
        }

        with self.assertRaises(exceptions.ValidationError) as cm:
            self.obj.validate_and_update(serializable=data)

        self.assertIn('serializable', cm.exception.message_dict)
        self.assertIn('string:', cm.exception.message_dict['serializable'][0])

    def test_update_error_bad_enum_value(self):
        data = {

            'an_enum': 'not_a_value',
        }

        with self.assertRaises(exceptions.ValidationError) as cm:
            self.obj.validate_and_update(serializable=data)

        self.assertIn('serializable', cm.exception.message_dict)
        self.assertIn('an_enum:', cm.exception.message_dict['serializable'][0])
