import itertools
from typing import Sequence

import autograder.core.models as ag_models
from autograder.core.models.copy_project_and_course import copy_project
from autograder.utils.testing import UnitTestBase
import autograder.utils.testing.model_obj_builders as obj_build


class CopyProjectTestCase(UnitTestBase):
    def test_copy_project(self):
        project = obj_build.make_project()
        proj_file1 = obj_build.make_uploaded_file(project)
        proj_file2 = obj_build.make_uploaded_file(project)
        student_file1 = obj_build.make_expected_student_pattern(project)
        student_file2 = obj_build.make_expected_student_pattern(project)

        suite1 = obj_build.make_ag_test_suite(project, project_files_needed=[proj_file1],                                              student_files_needed=[student_file1])
        case1 = obj_build.make_ag_test_case(suite1)
        cmd1 = obj_build.make_full_ag_test_command(case1)
        cmd2 = obj_build.make_full_ag_test_command(case1, set_arbitrary_points=False)

        suite2 = obj_build.make_ag_test_suite(project, project_files_needed=[proj_file2],
                                              student_files_needed=[student_file2])
        case2 = obj_build.make_ag_test_case(suite2)
        cmd3 = obj_build.make_full_ag_test_command(case2, set_arbitrary_expected_vals=False)
        case3 = obj_build.make_ag_test_case(suite2)

        suite3 = obj_build.make_ag_test_suite(project)

        other_course = obj_build.make_course()
        new_project = copy_project(project, other_course)

        self.assertEqual(project.name, new_project.name)
        self.assertEqual(other_course, new_project.course)
        self.assertNotEqual(project.course, other_course)

        ignore_fields = ['pk', 'course', 'uploaded_files', 'expected_student_file_patterns']
        self.assertEqual(_pop_many(project.to_dict(), ignore_fields),
                         _pop_many(new_project.to_dict(), ignore_fields))


        self.assertEqual(project.uploaded_files.count(), new_project.uploaded_files.count())
        for old_file, new_file in itertools.zip_longest(
                sorted(project.uploaded_files.all(), key=lambda obj: obj.name),
                sorted(new_project.uploaded_files.all(), key=lambda obj: obj.name)):
            self.assertNotEqual(new_file.pk, old_file.pk)
            self.assertNotEqual(new_file.abspath, old_file.abspath)

            self.assertEqual(old_file.name, new_file.name)
            with old_file.open() as old_f, new_file.open() as new_f:
                self.assertEqual(old_f.read(), new_f.read())

        self.assertEqual(project.expected_student_file_patterns.count(),
                         new_project.expected_student_file_patterns.count())
        for old_pattern, new_pattern in itertools.zip_longest(
                project.expected_student_file_patterns.order_by('pattern'),
                new_project.expected_student_file_patterns.order_by('pattern')):
            self.assertNotEqual(old_pattern.pk, new_pattern.pk)

            self.assertEqual(_pop_many(old_pattern.to_dict(), ['pk', 'project']),
                             _pop_many(new_pattern.to_dict(), ['pk', 'project']))

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

        ignore_fields = ['pk', 'project', 'ag_test_suite', 'ag_test_case', 'ag_test_command']
        expected = _recursive_pop(
            [suite.to_dict() for suite in project.ag_test_suites.all()], ignore_fields)
        actual = _recursive_pop(
            [suite.to_dict() for suite in new_project.ag_test_suites.all()], ignore_fields)
        # print(expected)
        # print(actual)
        self.assertEqual(expected, actual)

    def test_copy_project_new_name_same_course(self):
        project = obj_build.make_project()
        name = 'steve'
        new_project = copy_project(project, project.course, name)
        self.assertEqual(new_project.course, project.course)
        self.assertNotEqual(project, new_project)
        self.assertEqual(name, new_project.name)


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
