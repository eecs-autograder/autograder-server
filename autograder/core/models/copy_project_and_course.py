from __future__ import annotations

import copy
from typing import Optional

from django.core.files.uploadedfile import SimpleUploadedFile
from django.db import transaction

from autograder import utils
from autograder.core.models.project.expected_student_file import ExpectedStudentFile
from autograder.handgrading.import_handgrading_rubric import import_handgrading_rubric

from .ag_test.ag_test_case import AGTestCase
from .ag_test.ag_test_command import AGTestCommand
from .ag_test.ag_test_suite import AGTestSuite
from .course import Course, Semester
from .mutation_test_suite import MutationTestSuite
from .project import InstructorFile, Project
from .sandbox_docker_image import SandboxDockerImage


@transaction.atomic()
def copy_course(course: Course,
                new_course_name: str,
                new_course_semester: Optional[Semester],
                new_course_year: Optional[int]) -> Course:
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


def copy_project(project: Project, target_course: Course,
                 new_project_name: Optional[str] = None) -> Project:
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
    copier = _ProjectCopier(project, target_course, new_project_name)
    return copier.do_copy()


class _ProjectCopier:
    def __init__(
        self,
        project: Project,
        target_course: Course,
        new_project_name: Optional[str] = None
    ):
        self._project_to_copy = project
        self._target_course = target_course
        self._new_project_name = new_project_name

        self._new_project: Project | None = None
        self._new_instructor_files_by_name: dict[str, InstructorFile] = {}
        self._new_student_files_by_name: dict[str, ExpectedStudentFile] = {}

    @transaction.atomic
    def do_copy(self) -> Project:
        # Note: Do NOT use copy.deepcopy here, as it can result in
        # self._project_to_copy's handgrading rubric getting deleted.
        self._new_project = Project.objects.get(pk=self._project_to_copy.pk)
        self._new_project.pk = None
        self._new_project.course = self._target_course
        self._new_project.hide_ultimate_submission_fdbk = True
        self._new_project.visible_to_students = False
        if self._new_project_name is not None:
            self._new_project.name = self._new_project_name

        self._new_project.full_clean()
        self._new_project.save()

        self._copy_instructor_files()
        self._copy_expected_student_files()

        self._copy_ag_tests()
        self._copy_mutation_suites()

        if hasattr(self._project_to_copy, 'handgrading_rubric'):
            import_handgrading_rubric(
                import_to=self._new_project, import_from=self._project_to_copy)

        return self._new_project

    def _copy_instructor_files(self) -> None:
        for instructor_file in self._project_to_copy.instructor_files.all():
            with instructor_file.open('rb') as f:
                new_file = InstructorFile.objects.validate_and_create(
                    project=self._new_project,
                    file_obj=SimpleUploadedFile(instructor_file.name, f.read()))
            self._new_instructor_files_by_name[new_file.name] = new_file

    def _copy_expected_student_files(self) -> None:
        assert self._new_project is not None
        new_student_files: list[ExpectedStudentFile] = []
        for student_file in self._project_to_copy.expected_student_files.all():
            student_file.pk = None
            student_file.project = self._new_project
            new_student_files.append(student_file)
        saved_new_student_files = ExpectedStudentFile.objects.bulk_create(new_student_files)
        self._new_student_files_by_name = {
            student_file.pattern: student_file for student_file in saved_new_student_files
        }

    def _copy_ag_tests(self) -> None:
        assert self._new_project is not None

        for suite in self._project_to_copy.ag_test_suites.all():
            instructor_files_needed = [
                self._new_instructor_files_by_name[instructor_file.name]
                for instructor_file in suite.instructor_files_needed.all()
            ]
            student_files_needed = [
                self._new_student_files_by_name[file_.pattern]
                for file_ in suite.student_files_needed.all()
            ]

            new_suite = AGTestSuite.objects.validate_and_create(
                project=self._new_project,
                instructor_files_needed=instructor_files_needed,
                student_files_needed=student_files_needed,
                sandbox_docker_image=_copy_sandbox_docker_image(
                    suite.sandbox_docker_image, self._new_project.course),
                **utils.exclude_dict(
                    suite.to_dict(),
                    ('pk', 'project') + tuple(AGTestSuite.get_serialize_related_fields()))
            )

            copy_from_test_cases = list(suite.ag_test_cases.all())
            copy_to_test_cases = []
            for test_case in copy_from_test_cases:
                new_test_case = copy.deepcopy(test_case)
                new_test_case.pk = None
                new_test_case.ag_test_suite = new_suite
                copy_to_test_cases.append(new_test_case)

            copy_to_test_cases_by_name = {
                test_case.name: test_case for test_case in copy_to_test_cases
            }
            AGTestCase.objects.bulk_create(copy_to_test_cases)

            commands = AGTestCommand.objects.select_related('ag_test_case').filter(
                ag_test_case__ag_test_suite=suite
            )
            new_commands = []
            for command in commands:
                new_command = copy.deepcopy(command)
                new_command.pk = None
                new_command.ag_test_case = copy_to_test_cases_by_name[command.ag_test_case.name]

                if command.stdin_instructor_file is not None:
                    filename = command.stdin_instructor_file.name
                    new_command.stdin_instructor_file = (
                        self._new_instructor_files_by_name[filename])

                if command.expected_stdout_instructor_file is not None:
                    filename = command.expected_stdout_instructor_file.name
                    new_command.expected_stdout_instructor_file = (
                        self._new_instructor_files_by_name[filename])

                if command.expected_stderr_instructor_file is not None:
                    filename = command.expected_stderr_instructor_file.name
                    new_command.expected_stderr_instructor_file = (
                        self._new_instructor_files_by_name[filename])

                new_commands.append(new_command)

            AGTestCommand.objects.bulk_create(new_commands)

    def _copy_mutation_suites(self) -> None:
        for mutation_suite in self._project_to_copy.mutation_test_suites.all():
            instructor_files_needed = [
                self._new_instructor_files_by_name[instructor_file.name]
                for instructor_file in mutation_suite.instructor_files_needed.all()
            ]
            student_files_needed = [
                self._new_student_files_by_name[file_.pattern]
                for file_ in mutation_suite.student_files_needed.all()
            ]

            assert self._new_project is not None
            MutationTestSuite.objects.validate_and_create(
                project=self._new_project,
                instructor_files_needed=instructor_files_needed,
                student_files_needed=student_files_needed,
                sandbox_docker_image=_copy_sandbox_docker_image(
                    mutation_suite.sandbox_docker_image, self._new_project.course),
                **utils.exclude_dict(
                    mutation_suite.to_dict(),
                    ('pk', 'project') + tuple(MutationTestSuite.get_serialize_related_fields()))
            )


def _copy_sandbox_docker_image(
    to_copy: SandboxDockerImage,
    target_course: Course
) -> SandboxDockerImage:
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
