import os

from django.core.exceptions import ValidationError

from autograder.core.models import Course, LateDaysRemaining, Semester

import autograder.core.utils as core_ut
from autograder.core.models.course import clear_cached_user_roles
from autograder.utils.testing import UnitTestBase

import autograder.utils.testing.model_obj_builders as obj_build


class CourseTestCase(UnitTestBase):
    def test_valid_create_with_defaults(self) -> None:
        name = "eecs280"
        course = Course.objects.validate_and_create(name=name)

        course.refresh_from_db()

        self.assertEqual(name, course.name)
        self.assertIsNone(course.semester)
        self.assertIsNone(course.year)
        self.assertEqual('', course.subtitle)
        self.assertEqual(0, course.num_late_days)

    def test_create_no_defaults(self) -> None:
        name = 'Waaaaaluigi'
        semester = Semester.winter
        year = 2014
        subtitle = 'Tiiime'
        late_days = 2
        course = Course.objects.validate_and_create(
            name=name, semester=semester, year=year, subtitle=subtitle, num_late_days=late_days)

        course.refresh_from_db()

        self.assertEqual(name, course.name)
        self.assertEqual(semester, course.semester)
        self.assertEqual(year, course.year)
        self.assertEqual(subtitle, course.subtitle)
        self.assertEqual(late_days, course.num_late_days)

    def test_course_ordering(self) -> None:
        eecs280su18 = Course.objects.validate_and_create(
            name='EECS 280', semester=Semester.summer, year=2018)
        eecs183w17 = Course.objects.validate_and_create(
            name='EECS 183', semester=Semester.winter, year=2017)
        eecs280w18 = Course.objects.validate_and_create(
            name='EECS 280', semester=Semester.winter, year=2018)
        eecs280f18 = Course.objects.validate_and_create(
            name='EECS 280', semester=Semester.fall, year=2018)
        eecs280sp18 = Course.objects.validate_and_create(
            name='EECS 280', semester=Semester.spring, year=2018)
        eecs280su17 = Course.objects.validate_and_create(
            name='EECS 280', semester=Semester.summer, year=2017)
        eecs280sp17 = Course.objects.validate_and_create(
            name='EECS 280', semester=Semester.spring, year=2017)
        eecs183su17 = Course.objects.validate_and_create(
            name='EECS 183', semester=Semester.summer, year=2017)
        eecs183sp17 = Course.objects.validate_and_create(
            name='EECS 183', semester=Semester.spring, year=2017)
        eecs183f17 = Course.objects.validate_and_create(
            name='EECS 183', semester=Semester.fall, year=2017)
        eecs280w17 = Course.objects.validate_and_create(
            name='EECS 280', semester=Semester.winter, year=2017)
        eecs280f17 = Course.objects.validate_and_create(
            name='EECS 280', semester=Semester.fall, year=2017)
        eecs183f16 = Course.objects.validate_and_create(
            name='EECS 183', semester=Semester.fall, year=2016)

        self.assertSequenceEqual(
            [
                eecs183f16,
                eecs183w17,
                eecs183sp17,
                eecs183su17,
                eecs183f17,

                eecs280w17,
                eecs280sp17,
                eecs280su17,
                eecs280f17,

                eecs280w18,
                eecs280sp18,
                eecs280su18,
                eecs280f18,
            ],
            Course.objects.all()
        )

    def test_exception_on_empty_name(self) -> None:
        with self.assertRaises(ValidationError) as cm:
            Course.objects.validate_and_create(name='')
        self.assertTrue('name' in cm.exception.message_dict)

    def test_exception_on_null_name(self) -> None:
        with self.assertRaises(ValidationError) as cm:
            Course.objects.validate_and_create(name=None)
        self.assertTrue('name' in cm.exception.message_dict)

    def test_exception_on_non_unique_name_no_year_or_semester(self) -> None:
        course = Course.objects.validate_and_create(name='Wuluigio')
        with self.assertRaises(ValidationError) as cm:
            Course.objects.validate_and_create(name=course.name)

    def test_error_non_unique_name_year_and_semester(self) -> None:
        Course.objects.validate_and_create(name='Coursey', semester='Fall', year=2018)
        with self.assertRaises(ValidationError) as cm:
            Course.objects.validate_and_create(name='Coursey', semester='Fall', year=2018)

    def test_error_invalid_year(self) -> None:
        with self.assertRaises(ValidationError) as cm:
            Course.objects.validate_and_create(name='Coursey', semester='Fall', year=1900)

    def test_error_negative_late_days(self) -> None:
        with self.assertRaises(ValidationError) as cm:
            Course.objects.validate_and_create(name='steve', num_late_days=-1)
        self.assertIn('num_late_days', cm.exception.message_dict)

    def test_serialization(self) -> None:
        expected_fields = [
            'pk',
            'name',
            'semester',
            'year',
            'subtitle',
            'num_late_days',
            'allowed_guest_domain',
            'last_modified',
        ]

        course = obj_build.make_course()
        serialized = course.to_dict()

        self.assertCountEqual(expected_fields, serialized.keys())

        serialized.pop('pk')
        serialized.pop('last_modified')

        course.validate_and_update(**serialized)


class LateDaysRemainingTestCase(UnitTestBase):
    def setUp(self) -> None:
        super().setUp()
        self.course = obj_build.make_course(num_late_days=4)

        self.no_tokens_used = LateDaysRemaining.objects.validate_and_create(
            course=self.course, user=obj_build.make_user())

        self.some_tokens_used = LateDaysRemaining.objects.validate_and_create(
            course=self.course, user=obj_build.make_user())
        self.some_tokens_used.late_days_used = 3
        self.some_tokens_used.save()

        self.all_tokens_used = LateDaysRemaining.objects.validate_and_create(
            course=self.course, user=obj_build.make_user())
        self.all_tokens_used.late_days_used = 4
        self.all_tokens_used.save()

    def test_valid_create_with_defaults(self) -> None:
        user = obj_build.make_user()
        num_late_days = 2
        self.course.validate_and_update(num_late_days=num_late_days)
        remaining = LateDaysRemaining.objects.validate_and_create(
            course=self.course,
            user=user,
        )

        self.assertEqual(self.course, remaining.course)
        self.assertEqual(user, remaining.user)
        self.assertEqual(num_late_days, remaining.late_days_remaining)

    def test_error_already_exists_for_user_and_course(self) -> None:
        user = obj_build.make_user()
        LateDaysRemaining.objects.validate_and_create(
            course=self.course,
            user=user,
        )

        with self.assertRaises(ValidationError):
            LateDaysRemaining.objects.validate_and_create(
                course=self.course,
                user=user,
            )

    def test_error_negative_late_days_remaining(self) -> None:
        user = obj_build.make_user()
        late_days = LateDaysRemaining.objects.validate_and_create(
            course=self.course,
            user=user,
        )
        with self.assertRaises(ValidationError) as cm:
            late_days.late_days_remaining = -1

        self.assertIn('late_days_remaining', cm.exception.message_dict)

    def test_individual_given_extra_tokens(self) -> None:
        self.assertEqual(4, self.no_tokens_used.late_days_remaining)
        self.no_tokens_used.late_days_remaining = 5
        self.no_tokens_used.save()
        self.no_tokens_used.refresh_from_db()
        self.assertEqual(5, self.no_tokens_used.late_days_remaining)
        self.assertEqual(0, self.no_tokens_used.late_days_used)

        self.assertEqual(1, self.some_tokens_used.late_days_remaining)
        self.some_tokens_used.late_days_remaining = 2
        self.some_tokens_used.save()
        self.some_tokens_used.refresh_from_db()
        self.assertEqual(2, self.some_tokens_used.late_days_remaining)
        self.assertEqual(3, self.some_tokens_used.late_days_used)

        self.assertEqual(0, self.all_tokens_used.late_days_remaining)
        self.all_tokens_used.late_days_remaining = 3
        self.all_tokens_used.save()
        self.all_tokens_used.refresh_from_db()
        self.assertEqual(3, self.all_tokens_used.late_days_remaining)
        self.assertEqual(4, self.all_tokens_used.late_days_used)

    def test_individual_tokens_given_extra_and_revoked(self) -> None:
        self.assertEqual(4, self.no_tokens_used.late_days_remaining)
        self.no_tokens_used.late_days_remaining = 6
        self.no_tokens_used.save()
        self.no_tokens_used.refresh_from_db()

        self.assertEqual(6, self.no_tokens_used.late_days_remaining)
        self.no_tokens_used.late_days_remaining = 3
        self.no_tokens_used.save()
        self.no_tokens_used.refresh_from_db()
        self.assertEqual(3, self.no_tokens_used.late_days_remaining)
        self.assertEqual(0, self.no_tokens_used.late_days_used)

    def test_individual_tokens_revoked_then_given_extra(self) -> None:
        self.assertEqual(4, self.no_tokens_used.late_days_remaining)
        self.no_tokens_used.late_days_remaining = 3
        self.no_tokens_used.save()
        self.no_tokens_used.refresh_from_db()

        self.assertEqual(3, self.no_tokens_used.late_days_remaining)
        self.no_tokens_used.late_days_remaining = 5
        self.no_tokens_used.save()
        self.no_tokens_used.refresh_from_db()
        self.assertEqual(5, self.no_tokens_used.late_days_remaining)

    def test_tokens_remaining_set_to_zero(self) -> None:
        self.some_tokens_used.late_days_remaining = 0
        self.some_tokens_used.save()
        self.some_tokens_used.refresh_from_db()
        self.assertEqual(0, self.some_tokens_used.late_days_remaining)
        self.assertEqual(3, self.some_tokens_used.late_days_used)

    def test_invalid_set_late_days_remaining_to_be_negative(self) -> None:
        with self.assertRaises(ValidationError) as cm:
            self.some_tokens_used.late_days_remaining = -1
            self.some_tokens_used.save()

        self.assertIn('late_days_remaining', cm.exception.message_dict)

    def test_individual_group_given_extra_tokens_twice(self) -> None:
        self.some_tokens_used.late_days_remaining = 2
        self.some_tokens_used.save()
        self.some_tokens_used.refresh_from_db()
        self.assertEqual(2, self.some_tokens_used.late_days_remaining)
        self.assertEqual(3, self.some_tokens_used.late_days_used)

        self.some_tokens_used.late_days_remaining = 3
        self.some_tokens_used.save()
        self.some_tokens_used.refresh_from_db()
        self.assertEqual(3, self.some_tokens_used.late_days_remaining)
        self.assertEqual(3, self.some_tokens_used.late_days_used)

    def test_course_token_count_lowered_then_raised(self) -> None:
        self.assertEqual(0, self.all_tokens_used.late_days_remaining)
        self.assertEqual(1, self.some_tokens_used.late_days_remaining)
        self.assertEqual(4, self.no_tokens_used.late_days_remaining)

        self.course.validate_and_update(num_late_days=self.course.num_late_days - 2)

        self.no_tokens_used.refresh_from_db()
        self.some_tokens_used.refresh_from_db()
        self.all_tokens_used.refresh_from_db()

        self.assertEqual(0, self.all_tokens_used.late_days_remaining)
        self.assertEqual(0, self.some_tokens_used.late_days_remaining)
        self.assertEqual(2, self.no_tokens_used.late_days_remaining)

        self.course.validate_and_update(num_late_days=self.course.num_late_days + 3)

        self.no_tokens_used.refresh_from_db()
        self.some_tokens_used.refresh_from_db()
        self.all_tokens_used.refresh_from_db()

        self.assertEqual(1, self.all_tokens_used.late_days_remaining)
        self.assertEqual(2, self.some_tokens_used.late_days_remaining)
        self.assertEqual(5, self.no_tokens_used.late_days_remaining)

    def test_course_token_count_lowered_then_group_granted_extra(self) -> None:
        self.assertEqual(0, self.all_tokens_used.late_days_remaining)
        self.course.validate_and_update(
            num_late_days=self.course.num_late_days - 2)
        self.all_tokens_used.refresh_from_db()

        self.assertEqual(0, self.all_tokens_used.late_days_remaining)
        self.all_tokens_used.late_days_remaining = 2
        self.all_tokens_used.save()
        self.all_tokens_used.refresh_from_db()
        self.assertEqual(2, self.all_tokens_used.late_days_remaining)

        # If we re-raise the course count, the user's count should go up
        # by the same amount
        self.course.validate_and_update(
            num_late_days=self.course.num_late_days + 3)
        self.all_tokens_used.refresh_from_db()
        self.assertEqual(5, self.all_tokens_used.late_days_remaining)


class CourseFilesystemTestCase(UnitTestBase):
    def setUp(self) -> None:
        super().setUp()
        self.COURSE_NAME = 'eecs280'

    def test_course_root_dir_created(self) -> None:
        course = Course(name=self.COURSE_NAME)

        self.assertFalse(
            os.path.exists(os.path.dirname(core_ut.get_course_root_dir(course))))

        course.save()
        expected_course_root_dir = core_ut.get_course_root_dir(course)

        self.assertTrue(os.path.isdir(expected_course_root_dir))


class CourseRolesTestCase(UnitTestBase):
    def setUp(self) -> None:
        super().setUp()

        self.course = obj_build.make_course()
        self.user = obj_build.make_user()

    def test_is_admin(self) -> None:
        self.course = obj_build.make_course()
        self.user = obj_build.make_user()

        self.assertFalse(self.course.is_admin(self.user))

        self.course.admins.add(self.user)
        clear_cached_user_roles(self.course.pk)
        # Because of attribute caching, we need to load a fresh
        # object from the DB.
        self.course = Course.objects.get(pk=self.course.pk)
        self.assertTrue(self.course.is_admin(self.user))

    def test_is_staff(self) -> None:
        self.assertFalse(self.course.is_staff(self.user))

        self.course.staff.add(self.user)
        clear_cached_user_roles(self.course.pk)
        # Because of attribute caching, we need to load a fresh
        # object from the DB.
        self.course = Course.objects.get(pk=self.course.pk)
        self.assertTrue(self.course.is_staff(self.user))

    def test_admin_counts_as_staff(self) -> None:
        self.assertFalse(self.course.is_staff(self.user))

        self.course.admins.add(self.user)
        clear_cached_user_roles(self.course.pk)
        # Because of attribute caching, we need to load a fresh
        # object from the DB.
        self.course = Course.objects.get(pk=self.course.pk)
        self.assertTrue(self.course.is_staff(self.user))

    def test_is_student(self) -> None:
        self.assertFalse(self.course.is_student(self.user))

        self.course.students.add(self.user)
        clear_cached_user_roles(self.course.pk)
        # Because of attribute caching, we need to load a fresh
        # object from the DB.
        self.course = Course.objects.get(pk=self.course.pk)
        self.assertTrue(self.course.is_student(self.user))

    def test_is_handgrader(self) -> None:
        self.assertFalse(self.course.is_handgrader(self.user))

        self.course.handgraders.add(self.user)
        clear_cached_user_roles(self.course.pk)
        # Because of attribute caching, we need to load a fresh
        # object from the DB.
        self.course = Course.objects.get(pk=self.course.pk)
        self.assertTrue(self.course.is_handgrader(self.user))

    def test_is_allowed_guest(self) -> None:
        self.course.validate_and_update(allowed_guest_domain='')
        self.assertTrue(self.course.is_allowed_guest(self.user))

        self.course.validate_and_update(allowed_guest_domain='@llama.edu')
        self.assertFalse(self.course.is_allowed_guest(self.user))

        self.user.username += '@llama.edu'
        self.user.save()

        self.assertTrue(self.course.is_allowed_guest(self.user))

        self.course.validate_and_update(allowed_guest_domain='')
        self.assertTrue(self.course.is_allowed_guest(self.user))
