from typing import Optional

from django.core.files.uploadedfile import SimpleUploadedFile
from django.db import transaction

from autograder import utils
from autograder.handgrading.import_handgrading_rubric import import_handgrading_rubric
from .course import Course, Semester
from .project import Project, InstructorFile
from .ag_test.ag_test_suite import AGTestSuite
from .ag_test.ag_test_case import AGTestCase
from .ag_test.ag_test_command import AGTestCommand
from .student_test_suite import StudentTestSuite
from .sandbox_docker_image import SandboxDockerImage


@transaction.atomic()
def copy_project(project: Project, target_course: Course,
                 new_project_name: Optional[str]=None):
    """
    Makes a copy of the given course along with all instructor file,
     expected student file, test case, and handgrading data.
    Note that groups, submissions, and results (test case, handgrading,
    etc.) are NOT copied.
    :param project: The project to copy.
    :param target_course: The course the new project should belong to.
    :param new_project_name: The name of the new project.
    :return: The new project.
    """
    new_project = Project.objects.get(pk=project.pk)
    new_project.pk = None
    new_project.course = target_course
    new_project.hide_ultimate_submission_fdbk = True
    new_project.visible_to_students = False
    if new_project_name is not None:
        new_project.name = new_project_name

    new_project.full_clean()
    new_project.save()

    for instructor_file in project.instructor_files.all():
        with instructor_file.open('rb') as f:
            InstructorFile.objects.validate_and_create(
                project=new_project,
                file_obj=SimpleUploadedFile(instructor_file.name, f.read()))

    for student_file in project.expected_student_files.all():
        student_file.pk = None
        student_file.project = new_project
        student_file.save()

    _copy_ag_tests(project, new_project)
    _copy_student_suites(project, new_project)

    if hasattr(project, 'handgrading_rubric'):
        import_handgrading_rubric(import_to=new_project, import_from=project)

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

        new_suite = AGTestSuite.objects.validate_and_create(
            project=new_project,
            instructor_files_needed=instructor_files_needed,
            student_files_needed=student_files_needed,
            sandbox_docker_image=_copy_sandbox_docker_image(
                suite.sandbox_docker_image, new_project.course),
            **utils.exclude_dict(
                suite.to_dict(),
                ('pk', 'project') + AGTestSuite.get_serialize_related_fields())
        )

        for case in suite.ag_test_cases.all():
            new_case = AGTestCase.objects.validate_and_create(
                ag_test_suite=new_suite,
                **utils.exclude_dict(
                    case.to_dict(),
                    ('pk', 'ag_test_suite') + AGTestCase.get_serialize_related_fields())
            )

            for cmd in case.ag_test_commands.all():
                stdin_instructor_file = None
                if cmd.stdin_instructor_file is not None:
                    stdin_instructor_file = utils.find_if(
                        new_project.instructor_files.all(),
                        lambda instr_file: instr_file.name == cmd.stdin_instructor_file.name)

                expected_stdout_instructor_file = None
                if cmd.expected_stdout_instructor_file is not None:
                    expected_stdout_instructor_file = utils.find_if(
                        new_project.instructor_files.all(),
                        lambda instr_file:
                            instr_file.name == cmd.expected_stdout_instructor_file.name
                    )

                expected_stderr_instructor_file = None
                if cmd.expected_stderr_instructor_file is not None:
                    expected_stderr_instructor_file = utils.find_if(
                        new_project.instructor_files.all(),
                        lambda instr_file:
                            instr_file.name == cmd.expected_stderr_instructor_file.name
                    )

                AGTestCommand.objects.validate_and_create(
                    ag_test_case=new_case,
                    stdin_instructor_file=stdin_instructor_file,
                    expected_stdout_instructor_file=expected_stdout_instructor_file,
                    expected_stderr_instructor_file=expected_stderr_instructor_file,
                    **utils.exclude_dict(
                        cmd.to_dict(),
                        ('pk', 'ag_test_case') + AGTestCommand.get_serialize_related_fields())
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
        StudentTestSuite.objects.validate_and_create(
            project=new_project,
            instructor_files_needed=instructor_files_needed,
            student_files_needed=student_files_needed,
            sandbox_docker_image=_copy_sandbox_docker_image(
                student_suite.sandbox_docker_image, new_project.course),
            **utils.exclude_dict(
                student_suite.to_dict(),
                ('pk', 'project') + StudentTestSuite.get_serialize_related_fields())
        )


def _copy_sandbox_docker_image(to_copy: SandboxDockerImage, target_course: Course):
    if to_copy.course is None:
        return to_copy

    return SandboxDockerImage.objects.get_or_create(
        course=target_course,
        display_name=to_copy.display_name,
        defaults={
            'tag': to_copy.tag,
            # We haven't gotten rid of the name field yet, so
            # we need to generate a unique value to use.
            'name': to_copy.display_name + str(target_course.pk)
        },
    )[0]


@transaction.atomic()
def copy_course(course: Course,
                new_course_name: str,
                new_course_semester: Optional[Semester],
                new_course_year: Optional[int]):
    """
    Makes a copy of the given course and all its projects. The projects
    are copied using copy_project.
    The admin list is copied to the new project, but other permissions
    (staff, students, etc.) are not.
    :param course: The course to copy.
    :param new_course_name: The name for the new course.
    :param new_course_semester: The semester for the new course.
    :param new_course_year: The year for the new course.
    :return: The new course.
    """
    new_course = Course.objects.get(pk=course.pk)
    new_course.pk = None
    new_course.name = new_course_name
    new_course.semester = new_course_semester
    new_course.year = new_course_year

    new_course.full_clean()
    new_course.save()

    new_course.admins.add(*course.admins.all())

    for project in course.projects.all():
        copy_project(project, new_course)

    return new_course
