import uuid

from autograder.utils.testing.unit_test_base import UnitTestBase
import autograder.utils.testing.model_obj_builders as obj_build
import autograder.core.models as ag_models
from .copy_project import clone_project
from django.core.files.uploadedfile import SimpleUploadedFile


class CloneProjectTestCase(UnitTestBase):
    def test_empty_relationships(self):
        proj = obj_build.build_project(
            {'disallow_student_submissions': True,
             'disallow_group_registration': True,
             'allow_submissions_from_non_enrolled_students': True,
             'min_group_size': 2,
             'max_group_size': 5})
        self.do_clone_project_test(proj)

    def test_all_relationships(self):
        proj = obj_build.build_compiled_ag_test().project
        submissions, tests = obj_build.build_submissions_with_results(
            num_submissions=2, num_tests=4)
        file1 = random_uploaded_file(proj)
        file2 = random_uploaded_file(proj)
        file3 = random_uploaded_file(proj)
        pattern1 = random_pattern(proj)
        pattern2 = random_pattern(proj)
        pattern3 = random_pattern(proj)
        # test 0 no patterns no files
        # test 1 patterns no files
        tests[1].student_files_to_compile_together.add(pattern1, pattern2)
        tests[1].student_resource_files.add(pattern3, pattern1)
        # test 2 files no patterns
        tests[2].test_resource_files.add(file2)
        tests[2].project_files_to_compile_together.add(file2, file3)
        # test 3 patterns and files
        tests[3].student_files_to_compile_together.add(pattern1, pattern2, pattern3)
        tests[3].student_resource_files.add(pattern1, pattern2, pattern3)
        tests[3].test_resource_files.add(file1, file2, file3)
        tests[3].project_files_to_compile_together.add(file1, file2, file3)
        self.do_clone_project_test(proj)
        # cloning again tests that related objects across projects with
        # duplicate field values are not copied when they shouldn't be
        self.do_clone_project_test(proj)

    def do_clone_project_test(self, project):
        # compare properties
        cloned = clone_project(project, obj_build.build_course())
        cloned_dict = cloned.to_dict(exclude_fields=['pk', 'course'])
        project_dict = project.to_dict(exclude_fields=['pk', 'course'])
        self.assertEqual([], list(cloned.submission_groups.all()))
        self.assertEqual(cloned_dict, project_dict)
        self.assertNotEqual(cloned, project)
        self.assertNotEqual(cloned.course, project.course)
        for ag_test in cloned.autograder_test_cases.all():
            self.assertEqual([], list(ag_test.dependent_results.all()))

        exclude_fields = ['pk', 'project']
        self.check_project_relationship("uploaded_files",
                                        orig_proj=project,
                                        clone_proj=cloned,
                                        exclude_fields=exclude_fields,
                                        sort_field='file_obj')
        self.check_project_relationship("expected_student_file_patterns",
                                        orig_proj=project,
                                        clone_proj=cloned,
                                        exclude_fields=exclude_fields,
                                        sort_field='pattern')

        ag_test_exclude_fields = (
            exclude_fields +
            ag_models.AutograderTestCaseBase.RELATED_FILE_FIELD_NAMES
        )

        self.check_project_relationship("autograder_test_cases",
                                        orig_proj=project,
                                        clone_proj=cloned,
                                        exclude_fields=ag_test_exclude_fields,
                                        sort_field='name')

        self.check_ag_test_relationships(orig_proj=project, clone_proj=cloned)

    def check_project_relationship(self, relationship_name, orig_proj,
                                   clone_proj, exclude_fields, sort_field):
        cloned_objs = getattr(clone_proj, relationship_name).all().order_by(sort_field)
        orig_objs = getattr(orig_proj, relationship_name).all().order_by(sort_field)

        self.assertEqual(cloned_objs.count(), orig_objs.count())

        for cloned_obj, orig_obj in zip(cloned_objs, orig_objs):
            cloned_obj_dict = cloned_obj.to_dict(exclude_fields=exclude_fields)
            orig_obj_dict = orig_obj.to_dict(exclude_fields=exclude_fields)
            self.assertEqual(cloned_obj_dict, orig_obj_dict)
            self.assertNotEqual(cloned_obj.pk, orig_obj.pk)
            self.assertNotEqual(cloned_obj.project, orig_obj.project)

    def check_ag_test_relationships(self, orig_proj, clone_proj):
        exclude_fields = ['pk', 'project']
        cloned_tests = clone_proj.autograder_test_cases.all().order_by('name')
        proj_tests = orig_proj.autograder_test_cases.all().order_by('name')

        for cloned_test, proj_test in zip(cloned_tests, proj_tests):
            cloned_related_fields_dict = cloned_test.to_dict(
                include_fields=ag_models.AutograderTestCaseBase.RELATED_FILE_FIELD_NAMES)
            project_related_fields_dict = proj_test.to_dict(
                include_fields=ag_models.AutograderTestCaseBase.RELATED_FILE_FIELD_NAMES)

            for key, value in cloned_related_fields_dict.items():
                if not value and not project_related_fields_dict[key]:
                    continue

                self.assertNotEqual(set(project_related_fields_dict[key]), set(value))

                cloned_test_dicts = [
                    getattr(cloned_test, key).get(pk=pk).to_dict(
                        exclude_fields=exclude_fields) for pk in value
                ]

                project_test_dicts = [
                    getattr(proj_test, key).get(pk=pk).to_dict(
                        exclude_fields=exclude_fields)
                    for pk in project_related_fields_dict[key]
                ]

                self.assertCountEqual(cloned_test_dicts, project_test_dicts)


def random_uploaded_file(project):
    return ag_models.UploadedFile.objects.validate_and_create(
        file_obj=SimpleUploadedFile(name='file_name' + str(uuid.uuid4().hex),
                                    content=b'wooluuigo'),
        project=project)


def random_pattern(project):
    return ag_models.ExpectedStudentFilePattern.objects.validate_and_create(
        project=project, pattern='hi' + str(uuid.uuid4().hex))
