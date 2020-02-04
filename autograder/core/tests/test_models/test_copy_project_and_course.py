import itertools
from typing import Sequence

from django.core import exceptions

import autograder.core.models as ag_models
import autograder.utils.testing.model_obj_builders as obj_build
from autograder.core.models import Semester
from autograder.core.models.copy_project_and_course import copy_project, copy_course
from autograder.utils.testing import UnitTestBase

import autograder.handgrading.models as hg_models


class CopyProjectTestCase(UnitTestBase):
    def setUp(self):
        super().setUp()
        self._custom_image = ag_models.SandboxDockerImage.objects.get_or_create(
            display_name='Custom Image', tag='custom_image')[0]

    def test_copy_project(self):
        # In new project, hide_ultimate_submission_fdbk should be set to True,
        # visible_to_students should be set to False,
        # and guests_can_submit should be set to False
        project = obj_build.make_project(hide_ultimate_submission_fdbk=False,
                                         visible_to_students=True)
        instructor_file1 = obj_build.make_instructor_file(project)
        instructor_file2 = obj_build.make_instructor_file(project)
        student_file1 = obj_build.make_expected_student_file(project)
        student_file2 = obj_build.make_expected_student_file(project)

        suite1 = obj_build.make_ag_test_suite(project, instructor_files_needed=[instructor_file1],
                                              student_files_needed=[student_file1],
                                              sandbox_docker_image={'pk': self._custom_image.pk})
        case1 = obj_build.make_ag_test_case(suite1)
        cmd1 = obj_build.make_full_ag_test_command(
            case1,
            expected_stderr_source=ag_models.ExpectedOutputSource.instructor_file,
            expected_stderr_instructor_file=instructor_file2)
        cmd2 = obj_build.make_full_ag_test_command(
            case1, set_arbitrary_points=False,
            expected_stdout_source=ag_models.ExpectedOutputSource.instructor_file,
            expected_stdout_instructor_file=instructor_file1)

        suite2 = obj_build.make_ag_test_suite(
            project,
            instructor_files_needed=[instructor_file1, instructor_file2],
            student_files_needed=[student_file2])
        case2 = obj_build.make_ag_test_case(suite2)
        cmd3 = obj_build.make_full_ag_test_command(
            case2, set_arbitrary_expected_vals=False,
            stdin_source=ag_models.StdinSource.instructor_file,
            stdin_instructor_file=instructor_file2)
        case3 = obj_build.make_ag_test_case(suite2)

        suite3 = obj_build.make_ag_test_suite(project)

        student_suite1 = obj_build.make_student_test_suite(
            project,
            sandbox_docker_image={'pk': self._custom_image.pk},
            instructor_files_needed=[instructor_file1, instructor_file2],
            student_files_needed=[student_file1],
            setup_command={
                'name': 'stave',
                'cmd': 'yorp'
            })

        student_suite2 = obj_build.make_student_test_suite(
            project,
            instructor_files_needed=[instructor_file1],
            student_files_needed=[student_file1, student_file2])

        student_suite3 = obj_build.make_student_test_suite(project)

        handgrading_rubric = hg_models.HandgradingRubric.objects.validate_and_create(
            project=project,
            points_style=hg_models.PointsStyle.start_at_max_and_subtract,
            max_points=42,
            show_grades_and_rubric_to_students=True,
            handgraders_can_leave_comments=True,
            handgraders_can_adjust_points=True
        )

        criterion1 = hg_models.Criterion.objects.validate_and_create(
            handgrading_rubric=handgrading_rubric,
            short_description='nisoeta noiresta ',
            long_description=';qywuflp~QYWFPLu',
            points=-4
        )
        criterion2 = hg_models.Criterion.objects.validate_and_create(
            handgrading_rubric=handgrading_rubric,
            short_description='uwfvmc,n',
            long_description='qy;unmcrvcoe',
            points=-2
        )

        annotation1 = hg_models.Annotation.objects.validate_and_create(
            handgrading_rubric=handgrading_rubric,
            short_description='steve',
            long_description='steveluigi',
            deduction=-3,
            max_deduction=-9
        )
        annotation2 = hg_models.Annotation.objects.validate_and_create(
            handgrading_rubric=handgrading_rubric,
            short_description='stove',
            long_description='stovio',
            deduction=-5,
            max_deduction=-10
        )

        # --------------------------------------------------------------

        other_course = obj_build.make_course()
        new_project = copy_project(project, other_course)

        self.assertTrue(new_project.hide_ultimate_submission_fdbk)
        self.assertFalse(new_project.visible_to_students)

        self.assertEqual(project.name, new_project.name)
        self.assertEqual(other_course, new_project.course)
        self.assertNotEqual(project.course, other_course)

        ignore_fields = ['pk', 'course', 'last_modified',
                         'instructor_files', 'expected_student_files']
        expected_ag_tests = _pop_many(project.to_dict(), ignore_fields)
        expected_ag_tests.update(
            {'visible_to_students': False, 'hide_ultimate_submission_fdbk': True})
        self.assertEqual(expected_ag_tests, _pop_many(new_project.to_dict(), ignore_fields))

        self.assertEqual(project.instructor_files.count(), new_project.instructor_files.count())
        for old_file, new_file in itertools.zip_longest(
                sorted(project.instructor_files.all(), key=lambda obj: obj.name),
                sorted(new_project.instructor_files.all(), key=lambda obj: obj.name)):
            self.assertNotEqual(new_file.pk, old_file.pk)
            self.assertNotEqual(new_file.abspath, old_file.abspath)

            self.assertEqual(old_file.name, new_file.name)
            with old_file.open() as old_f, new_file.open() as new_f:
                self.assertEqual(old_f.read(), new_f.read())

        self.assertEqual(project.expected_student_files.count(),
                         new_project.expected_student_files.count())
        for old_expected_file, new_expected_file in itertools.zip_longest(
                project.expected_student_files.order_by('pattern'),
                new_project.expected_student_files.order_by('pattern')):
            self.assertNotEqual(old_expected_file.pk, new_expected_file.pk)

            expected_file_ignore_fields = ['pk', 'project', 'last_modified']
            self.assertEqual(_pop_many(old_expected_file.to_dict(), expected_file_ignore_fields),
                             _pop_many(new_expected_file.to_dict(), expected_file_ignore_fields))

        old_suite_pks = {suite.pk for suite in project.ag_test_suites.all()}
        new_suite_pks = {suite.pk for suite in new_project.ag_test_suites.all()}
        self.assertTrue(old_suite_pks.isdisjoint(new_suite_pks))

        old_case_pks = {case.pk for case in
                        ag_models.AGTestCase.objects.filter(ag_test_suite__project=project)}
        new_case_pks = {case.pk for case in
                        ag_models.AGTestCase.objects.filter(ag_test_suite__project=new_project)}
        self.assertTrue(old_case_pks.isdisjoint(new_case_pks))

        old_cmd_pks = {
            cmd.pk for cmd in ag_models.AGTestCommand.objects.filter(
                ag_test_case__ag_test_suite__project=project)}
        new_cmd_pks = {
            cmd.pk for cmd in ag_models.AGTestCommand.objects.filter(
                ag_test_case__ag_test_suite__project=new_project)}
        self.assertTrue(old_cmd_pks.isdisjoint(new_cmd_pks))

        old_student_suite_pks = {suite.pk for suite in project.student_test_suites.all()}
        new_student_suite_pks = {suite.pk for suite in new_project.student_test_suites.all()}
        self.assertTrue(old_student_suite_pks.isdisjoint(new_student_suite_pks))

        ignore_fields = ['pk', 'project', 'last_modified',
                         'ag_test_suite', 'ag_test_case', 'ag_test_command']
        expected_ag_tests = _recursive_pop(
            [suite.to_dict() for suite in project.ag_test_suites.all()], ignore_fields)
        for dict_ in expected_ag_tests:
            dict_['instructor_files_needed'].sort(key=lambda obj: obj['name'])
            dict_['student_files_needed'].sort(key=lambda obj: obj['pattern'])
        actual_ag_tests = _recursive_pop(
            [suite.to_dict() for suite in new_project.ag_test_suites.all()], ignore_fields)
        for dict_ in actual_ag_tests:
            dict_['instructor_files_needed'].sort(key=lambda obj: obj['name'])
            dict_['student_files_needed'].sort(key=lambda obj: obj['pattern'])
        self.assertEqual(expected_ag_tests, actual_ag_tests)

        expected_student_suites = _recursive_pop(
            [suite.to_dict() for suite in project.student_test_suites.all()], ignore_fields)
        for dict_ in expected_student_suites:
            dict_['instructor_files_needed'].sort(key=lambda obj: obj['name'])
            dict_['student_files_needed'].sort(key=lambda obj: obj['pattern'])
        actual_student_suites = _recursive_pop(
            [suite.to_dict() for suite in new_project.student_test_suites.all()], ignore_fields)
        for dict_ in actual_student_suites:
            dict_['instructor_files_needed'].sort(key=lambda obj: obj['name'])
            dict_['student_files_needed'].sort(key=lambda obj: obj['pattern'])
        self.assertEqual(expected_student_suites, actual_student_suites)

        new_rubric = new_project.handgrading_rubric
        self.assertNotEqual(handgrading_rubric.pk, new_rubric.pk)

        self.assertFalse(new_rubric.show_grades_and_rubric_to_students)

        old_criterion_pks = {criterion.pk for criterion in handgrading_rubric.criteria.all()}
        new_criterion_pks = {criterion.pk for criterion in new_rubric.criteria.all()}
        self.assertTrue(old_criterion_pks.isdisjoint(new_criterion_pks))

        old_annotation_pks = {annotation.pk for annotation in handgrading_rubric.annotations.all()}
        new_annotation_pks = {annotation.pk for annotation in new_rubric.annotations.all()}
        self.assertTrue(old_annotation_pks.isdisjoint(new_annotation_pks))

        handgrading_exclude_fields = [
            'pk', 'last_modified', 'project',
            'show_grades_and_rubric_to_students', 'handgrading_rubric'
        ]
        expected_handgrading_rubric = _recursive_pop(handgrading_rubric.to_dict(),
                                                     handgrading_exclude_fields)
        actual_handgrading_rubric = _recursive_pop(new_rubric.to_dict(),
                                                   handgrading_exclude_fields)
        self.assertEqual(2, new_rubric.criteria.count())
        self.assertEqual(2, new_rubric.annotations.count())

        self.maxDiff = None
        self.assertEqual(expected_handgrading_rubric, actual_handgrading_rubric)

    def test_copy_project_new_name_same_course(self):
        project = obj_build.make_project()
        name = 'steve'
        new_project = copy_project(project, project.course, name)
        self.assertEqual(new_project.course, project.course)
        self.assertNotEqual(project, new_project)
        self.assertEqual(name, new_project.name)

    def test_error_non_unique_name(self):
        project = obj_build.make_project()
        with self.assertRaises(exceptions.ValidationError):
            copy_project(project, project.course, project.name)

    def test_copy_project_no_handgrading_rubric(self):
        project = obj_build.make_project()
        self.assertFalse(hasattr(project, 'handgrading_rubric'))
        new_project = copy_project(project, project.course, new_project_name='Projy')
        self.assertFalse(hasattr(new_project, 'handgrading_rubric'))


class SandboxImageCopyingTestCase(UnitTestBase):
    @classmethod
    def setUpTestData(cls):
        ag_models.SandboxDockerImage.objects.exclude(display_name='Default').delete()

    def setUp(self):
        super().setUp()

        self.course1 = obj_build.make_course()
        self.course1_image = ag_models.SandboxDockerImage.objects.validate_and_create(
            course=self.course1,
            display_name='Custom Image',
            tag='custom_image'
        )
        self.course1_project = obj_build.make_project(self.course1)
        obj_build.make_ag_test_suite(self.course1_project, sandbox_docker_image=self.course1_image)
        obj_build.make_student_test_suite(
            self.course1_project, sandbox_docker_image=self.course1_image)

        self.course2 = obj_build.make_course()

    def test_copy_project_to_same_course_no_new_sandbox_images(self) -> None:
        original_num_images = ag_models.SandboxDockerImage.objects.count()
        new_project = copy_project(self.course1_project, self.course1, 'Copied project')
        self.assertEqual(
            self.course1_image, new_project.ag_test_suites.first().sandbox_docker_image)
        self.assertEqual(
            self.course1_image, new_project.student_test_suites.first().sandbox_docker_image)

        self.assertEqual(original_num_images, ag_models.SandboxDockerImage.objects.count())

    def test_copy_project_to_different_course_sandbox_images_copied(self) -> None:
        new_project = copy_project(self.course1_project, self.course2, 'Copied project')
        self.assertNotEqual(
            self.course1_image, new_project.ag_test_suites.first().sandbox_docker_image)
        self.assertNotEqual(
            self.course1_image, new_project.student_test_suites.first().sandbox_docker_image)

        self.assertEqual(new_project.ag_test_suites.first().sandbox_docker_image,
                         new_project.student_test_suites.first().sandbox_docker_image)

        new_image = new_project.ag_test_suites.first().sandbox_docker_image
        self.assertEqual(self.course1_image.display_name, new_image.display_name)
        self.assertEqual(self.course1_image.tag, new_image.tag)

        self.assertEqual(2, ag_models.SandboxDockerImage.objects.exclude(course=None).count())

    # Scenario:
    # - Two projects, P1 and P2, from different courses
    # - Both courses have an image with display_name "My Image"
    # - P1 is copied to P2's course
    # - The copy of P1 uses the existing version of "My Image" that
    #   belongs to P2's course instead of creating an additional
    #   "My Image", thus avoiding a name conflict.
    def test_copy_project_to_different_course_sandbox_image_name_conflicts_avoided(self) -> None:
        course2_image = ag_models.SandboxDockerImage.objects.validate_and_create(
            course=self.course2,
            display_name='Custom Image',
            tag='custom_image'
        )
        course2_project = obj_build.make_project(self.course2)

        new_project = copy_project(self.course1_project, self.course2, 'Copied project')
        self.assertEqual(
            course2_image, new_project.ag_test_suites.first().sandbox_docker_image)
        self.assertEqual(
            course2_image, new_project.student_test_suites.first().sandbox_docker_image)

        self.assertEqual(2, ag_models.SandboxDockerImage.objects.exclude(course=None).count())


def _pop_many(dict_: dict, keys: Sequence[str]):
    for key in keys:
        dict_.pop(key, None)

    return dict_


def _recursive_pop(obj, keys: Sequence[str]):
    if isinstance(obj, dict):
        _pop_many(obj, keys)
        for value in obj.values():
            _recursive_pop(value, keys)
    elif isinstance(obj, list):
        for item in obj:
            _recursive_pop(item, keys)

    return obj


class CopyCourseTestCase(UnitTestBase):
    def test_copy_course(self):
        proj1 = obj_build.make_project()
        course = proj1.course
        proj2 = obj_build.make_project(course)

        admins = obj_build.make_admin_users(course, 4)
        staff = obj_build.make_staff_users(course, 3)
        students = obj_build.make_student_users(course, 5)
        handgraders = obj_build.make_handgrader_users(course, 2)

        self.assertNotEqual(0, course.staff.count())
        self.assertNotEqual(0, course.students.count())
        self.assertNotEqual(0, course.handgraders.count())

        name = 'stove'
        new_course = copy_course(course, name, Semester.summer, 2019)

        self.assertEqual(name, new_course.name)
        self.assertEqual(Semester.summer, new_course.semester)
        self.assertEqual(2019, new_course.year)

        self.assertCountEqual(admins, new_course.admins.all())
        self.assertSequenceEqual([], new_course.staff.all())
        self.assertSequenceEqual([], new_course.students.all())
        self.assertSequenceEqual([], new_course.handgraders.all())

        old_project_pks = {proj.pk for proj in course.projects.all()}
        new_project_pks = {proj.pk for proj in new_course.projects.all()}
        self.assertTrue(old_project_pks.isdisjoint(new_project_pks))

        self.assertSetEqual({proj.name for proj in course.projects.all()},
                            {proj.name for proj in new_course.projects.all()})

    def test_error_non_unique_name(self):
        course = obj_build.make_course()
        with self.assertRaises(exceptions.ValidationError):
            copy_course(course, new_course_name=course.name,
                        new_course_semester=None, new_course_year=None)
