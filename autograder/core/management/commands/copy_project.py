#! /usr/bin/env python3

from django.core.management.base import BaseCommand
from django.db import transaction
import autograder.core.models as ag_models
from django.core.files.uploadedfile import SimpleUploadedFile


class Command(BaseCommand):
    help = 'Change to something helpful'

    def add_arguments(self, parser):
        parser.add_argument('course_name')
        parser.add_argument('project_name')
        parser.add_argument('target_course_name')

    def handle(self, course_name, project_name, target_course_name, *args, **kwargs):
        print(course_name, project_name, target_course_name)
        target_course = ag_models.Course.objects.get(name=target_course_name)
        source_project = ag_models.Project.objects.get(name=project_name, course__name=course_name)
        clone_project(project=source_project, target_course=target_course)


def clone_project(project, target_course):

    with transaction.atomic():
        new_proj = ag_models.Project.objects.validate_and_create(
            **project.to_dict(exclude_fields=['pk', 'course']), course=target_course)

        for uploaded_file in project.uploaded_files.all():
            new_file = SimpleUploadedFile(uploaded_file.name, uploaded_file.file_obj.read())
            ag_models.UploadedFile.objects.validate_and_create(
                file_obj=new_file, project=new_proj)

        for pattern in project.expected_student_file_patterns.all():
            ag_models.ExpectedStudentFilePattern.objects.validate_and_create(
                **pattern.to_dict(exclude_fields=['pk', 'project']), project=new_proj)

        _clone_test_cases(orig_proj=project, new_proj=new_proj)

        return new_proj


def _clone_test_cases(orig_proj, new_proj):
    for test_case in orig_proj.autograder_test_cases.all():
        test_case_dict = test_case.to_dict(
            exclude_fields=['pk', 'project', 'test_resource_files', 'student_resource_files',
                            'project_files_to_compile_together',
                            'student_files_to_compile_together'])
        for fdbk_field in ag_models.AutograderTestCaseBase.FDBK_FIELD_NAMES:
            test_case_dict[fdbk_field] = (
                ag_models.FeedbackConfig.objects.validate_and_create(
                    **test_case_dict[fdbk_field])
            )

        new_test_case = ag_models.AutograderTestCaseFactory.validate_and_create(
            project=new_proj, **test_case_dict)

        test_resource_file_names = [file_.name for file_ in
                                    test_case.test_resource_files.all()]

        new_test_case.test_resource_files.set(
            [file_ for file_ in new_proj.uploaded_files.all() if
             file_.name in test_resource_file_names])

        student_patterns = [pattern.pattern for pattern in
                            test_case.student_resource_files.all()]
        new_test_case.student_resource_files.set(
            new_proj.expected_student_file_patterns.filter(
                pattern__in=student_patterns))

        compiled_project_file_names = [
            file_.name for file_ in
            test_case.project_files_to_compile_together.all()
        ]
        new_test_case.project_files_to_compile_together.set(
            [file_ for file_ in new_proj.uploaded_files.all() if
             file_.name in compiled_project_file_names])

        compiled_student_patterns = [
            pattern.pattern for pattern in
            test_case.student_files_to_compile_together.all()
        ]
        new_test_case.student_files_to_compile_together.set(
            new_proj.expected_student_file_patterns.filter(
                pattern__in=compiled_student_patterns))

    # load project
    # load target course
    # put into fn
    #
    # load thing
    # make dict, excluding things
    # pass dict to validate and create with unpacking syntax
    #
    #
    # 1. make project
    # 2. make patterns and files, passing in p
    # 3. Create ag test case and link to project, then link to pattern and file
    #   fields: test resource files, student resource files, project files to compile,
    #   student files to compile
    #
    # django doc on models (but always use validate_and_create and
    # validate_and_update)
