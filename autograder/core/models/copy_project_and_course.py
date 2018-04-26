from django.core.files.uploadedfile import SimpleUploadedFile
from django.db import transaction

import autograder.core.models as ag_models
from autograder import utils


@transaction.atomic()
def copy_project(project: ag_models.Project, target_course: ag_models.Course,
                 new_project_name: str=None):
    new_project = ag_models.Project.objects.get(pk=project.pk)
    new_project.pk = None
    new_project.course = target_course
    new_project.hide_ultimate_submission_fdbk = True
    new_project.visible_to_students = False
    if new_project_name is not None:
        new_project.name = new_project_name

    new_project.save()

    for instructor_file in project.instructor_files.all():
        with instructor_file.open('rb') as f:
            ag_models.InstructorFile.objects.validate_and_create(
                project=new_project,
                file_obj=SimpleUploadedFile(instructor_file.name, f.read()))

    for student_file in project.expected_student_files.all():
        student_file.pk = None
        student_file.project = new_project
        student_file.save()

    _copy_ag_tests(project, new_project)
    _copy_student_suites(project, new_project)

    return new_project


def _copy_ag_tests(project, new_project):
    for suite in project.ag_test_suites.all():
        instructor_files_needed = [
            file_ for file_ in new_project.instructor_files.all()
            if utils.find_if(suite.instructor_files_needed.all(),
                             lambda instr_file: instr_file.name == file_.name)
        ]
        student_files_needed = list(
            new_project.expected_student_files.filter(
                pattern__in=[
                    student_file.pattern for student_file in suite.student_files_needed.all()]))

        new_suite = ag_models.AGTestSuite.objects.validate_and_create(
            project=new_project,
            instructor_files_needed=instructor_files_needed,
            student_files_needed=student_files_needed,
            **utils.exclude_dict(
                suite.to_dict(),
                ('pk', 'project') + ag_models.AGTestSuite.get_serialize_related_fields())
        )

        for case in suite.ag_test_cases.all():
            new_case = ag_models.AGTestCase.objects.validate_and_create(
                ag_test_suite=new_suite,
                **utils.exclude_dict(
                    case.to_dict(),
                    ('pk', 'ag_test_suite') + ag_models.AGTestCase.get_serialize_related_fields())
            )

            for cmd in case.ag_test_commands.all():
                stdin_instructor_file = None
                if cmd.stdin_instructor_file is not None:
                    stdin_instructor_file = utils.find_if(
                        new_project.instructor_files.all(),
                        lambda instr_file: instr_file.name == cmd.stdin_instructor_file.name)

                expected_ = None
                if cmd.expected_ is not None:
                    expected_ = utils.find_if(
                        new_project.instructor_files.all(),
                        lambda instr_file: instr_file.name == cmd.expected_.name
                    )

                expected_stderr_instructor_file = None
                if cmd.expected_stderr_instructor_file is not None:
                    expected_stderr_instructor_file = utils.find_if(
                        new_project.instructor_files.all(),
                        lambda instr_file: instr_file.name == cmd.expected_stderr_instructor_file.name
                    )

                ag_models.AGTestCommand.objects.validate_and_create(
                    ag_test_case=new_case,
                    stdin_instructor_file=stdin_instructor_file,
                    expected_=expected_,
                    expected_stderr_instructor_file=expected_stderr_instructor_file,
                    **utils.exclude_dict(cmd.to_dict(),
                                         ('pk', 'ag_test_case') +
                                         ag_models.AGTestCommand.get_serialize_related_fields())
                )


def _copy_student_suites(project, new_project):
    for student_suite in project.student_test_suites.all():
        instructor_files_needed = [
            file_ for file_ in new_project.instructor_files.all()
            if utils.find_if(student_suite.instructor_files_needed.all(),
                             lambda instr_file: instr_file.name == file_.name)
        ]
        student_files_needed = list(
            new_project.expected_student_files.filter(
                pattern__in=[
                    expected_file.pattern for expected_file in
                    student_suite.student_files_needed.all()
                ]
            )
        )
        ag_models.StudentTestSuite.objects.validate_and_create(
            project=new_project,
            instructor_files_needed=instructor_files_needed,
            student_files_needed=student_files_needed,
            **utils.exclude_dict(
                student_suite.to_dict(),
                ('pk', 'project') + ag_models.StudentTestSuite.get_serialize_related_fields())
        )


@transaction.atomic()
def copy_course(course: ag_models.Course, new_course_name: str):
    new_course = ag_models.Course.objects.get(pk=course.pk)
    new_course.pk = None
    new_course.name = new_course_name

    new_course.save()

    for project in course.projects.all():
        copy_project(project, new_course)

    return new_course
