import os

from django.core.exceptions import ValidationError

from autograder.core.models import Course, LateDaysRemaining, Semester

import autograder.core.utils as core_ut
from autograder.utils.testing import UnitTestBase

import autograder.utils.testing.model_obj_builders as obj_build


class CourseTestCase(UnitTestBase):
    def test_valid_create_with_defaults(self):
        name = "eecs280"
        course = Course.objects.validate_and_create(name=name)

        course.refresh_from_db()

        self.assertEqual(name, course.name)
        self.assertIsNone(course.semester)
        self.assertIsNone(course.year)
        self.assertEqual('', course.subtitle)
        self.assertEqual(0, course.num_late_days)

    def test_create_no_defaults(self):
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

    def test_course_ordering(self):
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

    def test_exception_on_empty_name(self):
        with self.assertRaises(ValidationError) as cm:
            Course.objects.validate_and_create(name='')
        self.assertTrue('name' in cm.exception.message_dict)

    def test_exception_on_null_name(self):
        with self.assertRaises(ValidationError) as cm:
            Course.objects.validate_and_create(name=None)
        self.assertTrue('name' in cm.exception.message_dict)

    def test_exception_on_non_unique_name_no_year_or_semester(self):
        course = Course.objects.validate_and_create(name='Wuluigio')
        with self.assertRaises(ValidationError) as cm:
            Course.objects.validate_and_create(name=course.name)

    def test_error_non_unique_name_year_and_semester(self):
        Course.objects.validate_and_create(name='Coursey', semester='Fall', year=2018)
        with self.assertRaises(ValidationError) as cm:
            Course.objects.validate_and_create(name='Coursey', semester='Fall', year=2018)

    def test_error_invalid_year(self):
        with self.assertRaises(ValidationError) as cm:
            Course.objects.validate_and_create(name='Coursey', semester='Fall', year=1900)

    def test_error_negative_late_days(self):
        with self.assertRaises(ValidationError) as cm:
            Course.objects.validate_and_create(name='steve', num_late_days=-1)
        self.assertIn('num_late_days', cm.exception.message_dict)

    def test_serialization(self):
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
    def setUp(self):
        super().setUp()
        self.course = obj_build.make_course()
        self.user = obj_build.make_user()

    def test_valid_create_with_defaults(self):
        num_late_days = 2
        self.course.validate_and_update(num_late_days=num_late_days)
        remaining = LateDaysRemaining.objects.validate_and_create(
            course=self.course,
            user=self.user,
        )

        self.assertEqual(self.course, remaining.course)
        self.assertEqual(self.user, remaining.user)
        self.assertEqual(num_late_days, remaining.late_days_remaining)

    def test_valid_create(self):
        late_days_remaining = 2
        remaining = LateDaysRemaining.objects.validate_and_create(
            course=self.course,
            user=self.user,
            late_days_remaining=late_days_remaining
        )

        self.assertEqual(self.course, remaining.course)
        self.assertEqual(self.user, remaining.user)
        self.assertEqual(late_days_remaining, remaining.late_days_remaining)

    def test_error_already_exists_for_user_and_course(self):
        LateDaysRemaining.objects.validate_and_create(
            course=self.course,
            user=self.user,
            late_days_remaining=1
        )

        with self.assertRaises(ValidationError):
            LateDaysRemaining.objects.validate_and_create(
                course=self.course,
                user=self.user,
                late_days_remaining=3
            )

    def test_error_negative_late_days_remaining(self):
        with self.assertRaises(ValidationError):
            LateDaysRemaining.objects.validate_and_create(
                course=self.course,
                user=self.user,
                late_days_remaining=-1
            )


class CourseFilesystemTestCase(UnitTestBase):
    def setUp(self):
        super().setUp()
        self.COURSE_NAME = 'eecs280'

    def test_course_root_dir_created(self):
        course = Course(name=self.COURSE_NAME)

        self.assertFalse(
            os.path.exists(os.path.dirname(core_ut.get_course_root_dir(course))))

        course.save()
        expected_course_root_dir = core_ut.get_course_root_dir(course)

        self.assertTrue(os.path.isdir(expected_course_root_dir))


class CourseRolesTestCase(UnitTestBase):
    def setUp(self):
        super().setUp()

        self.course = obj_build.make_course()
        self.user = obj_build.make_user()

    def test_is_admin(self):
        self.course = obj_build.make_course()
        self.user = obj_build.make_user()

        self.assertFalse(self.course.is_admin(self.user))

        self.course.admins.add(self.user)
        self.assertTrue(self.course.is_admin(self.user))

    def test_is_staff(self):
        self.assertFalse(self.course.is_staff(self.user))

        self.course.staff.add(self.user)
        self.assertTrue(self.course.is_staff(self.user))

    def test_admin_counts_as_staff(self):
        self.assertFalse(self.course.is_staff(self.user))

        self.course.admins.add(self.user)
        self.assertTrue(self.course.is_staff(self.user))

    def test_is_student(self):
        self.assertFalse(self.course.is_student(self.user))

        self.course.students.add(self.user)
        self.assertTrue(self.course.is_student(self.user))

    def test_is_handgrader(self):
        self.assertFalse(self.course.is_handgrader(self.user))

        self.course.handgraders.add(self.user)
        self.assertTrue(self.course.is_handgrader(self.user))

    def test_is_allowed_guest(self):
        self.course.validate_and_update(allowed_guest_domain='')
        self.assertTrue(self.course.is_allowed_guest(self.user))

        self.course.validate_and_update(allowed_guest_domain='@llama.edu')
        self.assertFalse(self.course.is_allowed_guest(self.user))

        self.user.username += '@llama.edu'
        self.user.save()

        self.assertTrue(self.course.is_allowed_guest(self.user))

        self.course.validate_and_update(allowed_guest_domain='')
        self.assertTrue(self.course.is_allowed_guest(self.user))
