from django.core import exceptions

from autograder import utils
from autograder.handgrading.import_handgrading_rubric import import_handgrading_rubric
from autograder.utils.testing import UnitTestBase
import autograder.utils.testing.model_obj_builders as obj_build

import autograder.handgrading.models as hg_models


class ImportHandgradingRubricTestCase(UnitTestBase):
    def setUp(self):
        super().setUp()
        self.project = obj_build.make_project()

        self.handgrading_rubric = hg_models.HandgradingRubric.objects.validate_and_create(
            project=self.project,
            points_style=hg_models.PointsStyle.start_at_max_and_subtract,
            max_points=42,
            show_grades_and_rubric_to_students=True,
            handgraders_can_leave_comments=True,
            handgraders_can_adjust_points=True
        )

        self.criterion1 = hg_models.Criterion.objects.validate_and_create(
            handgrading_rubric=self.handgrading_rubric,
            short_description='yip',
            long_description='yup',
            points=-4
        )
        self.criterion2 = hg_models.Criterion.objects.validate_and_create(
            handgrading_rubric=self.handgrading_rubric,
            short_description='yep',
            long_description='yap',
            points=-2
        )

        self.annotation1 = hg_models.Annotation.objects.validate_and_create(
            handgrading_rubric=self.handgrading_rubric,
            short_description='yop',
            long_description='yuuup',
            deduction=-3,
            max_deduction=-9
        )
        self.annotation2 = hg_models.Annotation.objects.validate_and_create(
            handgrading_rubric=self.handgrading_rubric,
            short_description='yiiiip',
            long_description='yorp',
            deduction=-5,
            max_deduction=-10
        )
    
    def test_import_handgrading_rubric(self):
        new_project = obj_build.make_project(course=self.project.course)
        import_handgrading_rubric(import_to=new_project, import_from=self.project)

        new_project.refresh_from_db()

        new_rubric = new_project.handgrading_rubric

        self.assertFalse(new_rubric.show_grades_and_rubric_to_students)

        self.assertNotEqual(new_project.handgrading_rubric.pk, self.project.handgrading_rubric.pk)

        ignore_fields = ['pk', 'last_modified']
        self.assertEqual(
            utils.exclude_dict(new_rubric.to_dict(),
                               ignore_fields + ['show_grades_and_rubric_to_students']),
            utils.exclude_dict(new_rubric.to_dict(),
                               ignore_fields + ['show_grades_and_rubric_to_students'])
        )

        related_ignore_fields = ignore_fields + ['handgrading_rubric']

        self.assertEqual(2, self.handgrading_rubric.criteria.count())
        self.assertEqual(2, new_rubric.criteria.count())
        for old, new in zip(self.handgrading_rubric.criteria.all(),
                            new_rubric.criteria.all()):
            self.assertNotEqual(old.pk, new.pk)
            self.assertEqual(utils.exclude_dict(old.to_dict(), related_ignore_fields),
                             utils.exclude_dict(new.to_dict(), related_ignore_fields))

        self.assertEqual(2, self.handgrading_rubric.annotations.count())
        self.assertEqual(2, new_rubric.annotations.count())
        for old, new in zip(self.handgrading_rubric.annotations.all(),
                            new_rubric.annotations.all()):
            self.assertNotEqual(old.pk, new.pk)
            self.assertEqual(utils.exclude_dict(old.to_dict(), related_ignore_fields),
                             utils.exclude_dict(new.to_dict(), related_ignore_fields))

    def test_old_rubric_deleted(self):
        new_project = obj_build.make_project(course=self.project.course)
        old_rubric = hg_models.HandgradingRubric.objects.validate_and_create(project=new_project)

        import_handgrading_rubric(import_to=new_project, import_from=self.project)

        with self.assertRaises(exceptions.ObjectDoesNotExist):
            old_rubric.refresh_from_db()
