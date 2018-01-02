from celery.result import GroupResult
from django.contrib.postgres.fields import ArrayField, JSONField
from django.core import exceptions
from django.db import models

from .task import Task
from .submission import Submission
from .project import Project
from .ag_test.ag_test_suite import AGTestSuite
from .ag_test.ag_test_case import AGTestCase
from .student_test_suite import StudentTestSuite


class RerunSubmissionsTask(Task):
    project = models.ForeignKey(Project, related_name='rerun_submission_tasks',
                                on_delete=models.CASCADE,
                                help_text="The Project this task belongs to.")

    rerun_all_submissions = models.BooleanField(
        default=True,
        help_text="""When True, indicates that all submissions for the specified
                     project should be rerun. Otherwise, only the submissions
                     whose primary keys are listed in submission_pks should be rerun.""")
    submission_pks = ArrayField(
        models.IntegerField(), blank=True, default=list,
        help_text="""When rerun_all_submissions is False, specifies which submissions
                     should be rerun.""")

    rerun_all_ag_test_suites = models.BooleanField(
        default=True,
        help_text="""When True, indicates that all AGTestSuites belonging
                     to the specified project should be rerun. Otherwise,
                     only the AGTestSuites specified in ag_test_suite_data should
                     be rerun.""")
    ag_test_suite_data = JSONField(
        blank=True, default=dict,
        help_text="""When rerun_all_ag_test_suites is False, specifies which
                     AGTestSuites should be rerun and which AGTestCases within
                     those suites should be rerun.
        Data format:
        {
            // Note: JSON format requires that keys are strings. Postgres
            // doesn't seem to care, but some JSON serializers might.
            "<ag_test_suite_pk>": [<ag_test_case_pk>, ...],
            ...
        }
        If an ag_test_suite_pk is mapped to an empty list, then all ag test cases
        belonging to that ag test suite will be rerun.""")

    rerun_all_student_test_suites = models.BooleanField(
        default=True,
        help_text="""When True, indicates that all StudentTestSuites belonging
                     to the specified project should be rerun. Otherwise,
                     only the StudentTestSuites specified in student_test_suite_pks
                     should be rerun.""")
    student_suite_pks = ArrayField(
        models.IntegerField(), blank=True, default=list,
        help_text="""When rerun_all_student_test_suites is False, specifies which
                     student test suites should be rerun.""")

    num_completed_subtasks = models.IntegerField(default=0)

    celery_group_result_id = models.UUIDField(blank=True, null=True, default=None)

    @property
    def progress(self):
        if self.rerun_all_submissions:
            num_submissions = Submission.objects.filter(
                submission_group__project=self.project).count()
        else:
            num_submissions = len(self.submission_pks)

        if self.rerun_all_ag_test_suites:
            num_ag_test_suites = AGTestSuite.objects.filter(project=self.project).count()
        else:
            num_ag_test_suites = len(self.ag_test_suite_data)

        if self.rerun_all_student_test_suites:
            num_student_suites = StudentTestSuite.objects.filter(project=self.project).count()
        else:
            num_student_suites = len(self.student_suite_pks)

        num_tasks = num_submissions * (num_ag_test_suites + num_student_suites)

        if num_tasks == 0:
            return 100

        return int(min((self.num_completed_subtasks / num_tasks) * 100, 100))

    def clean(self):
        super().clean()

        errors = {}

        if not self.rerun_all_submissions:
            submissions = Submission.objects.filter(
                pk__in=self.submission_pks, submission_group__project=self.project)
            found_pks = {submission.pk for submission in submissions}
            not_found_pks = set(self.submission_pks) - found_pks

            if not_found_pks:
                errors['submission_pks'] = (
                    'The following submissions do not belong to the project {}: {}'.format(
                        self.project.name, ', '.join((str(pk) for pk in not_found_pks))))

        if not self.rerun_all_ag_test_suites:
            ag_suites = AGTestSuite.objects.filter(
                pk__in=self.ag_test_suite_data.keys(), project=self.project)
            found_pks = {str(suite.pk) for suite in ag_suites}
            not_found_pks = {str(pk) for pk in self.ag_test_suite_data.keys()} - found_pks

            if not_found_pks:
                errors['ag_test_suite_data'] = (
                    'The following ag test suites do not belong to the project {}: {}'.format(
                        self.project.name, ', '.join(not_found_pks)))

            for suite_pk, ag_test_pks in self.ag_test_suite_data.items():
                ag_cases = AGTestCase.objects.filter(pk__in=ag_test_pks, ag_test_suite=suite_pk)
                found_pks = {case.pk for case in ag_cases}
                not_found_pks = set(ag_test_pks) - found_pks

                if not_found_pks:
                    if 'ag_test_suite_data' not in errors:
                        errors['ag_test_suite_data'] = []

                    errors['ag_test_suite_data'] += (
                        'The following ag test cases do not belong '
                        'to the ag test suite {}: {}'.format(
                            suite_pk, ', '.join((str(pk) for pk in not_found_pks))))

        if not self.rerun_all_student_test_suites:
            student_suites = StudentTestSuite.objects.filter(
                pk__in=self.student_suite_pks, project=self.project)
            found_pks = {suite.pk for suite in student_suites}
            not_found_pks = set(self.student_suite_pks) - found_pks

            if not_found_pks:
                errors['student_suite_pks'] = (
                    'The following student test suites do not belong to the project {}: {}'.format(
                        self.project.name, ', '.join((str(pk) for pk in not_found_pks))))

        if errors:
            raise exceptions.ValidationError(errors)

    SERIALIZABLE_FIELDS = [
        'pk',
        'progress',
        'error_msg',
        'creator',
        'created_at',
        'has_error',

        'project',

        'rerun_all_submissions',
        'submission_pks',
        'rerun_all_ag_test_suites',
        'ag_test_suite_data',
        'rerun_all_student_test_suites',
        'student_suite_pks',
    ]
