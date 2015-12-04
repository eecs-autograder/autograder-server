# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations
import django.core.validators
import jsonfield.fields
import autograder.models.fields
import autograder.models.project
import autograder.models.submission
import django.contrib.postgres.fields
import autograder.models.student_test_suite.student_test_suite_result


class Migration(migrations.Migration):

    dependencies = [
        ('contenttypes', '0002_remove_content_type_name'),
    ]

    operations = [
        migrations.CreateModel(
            name='_SubmittedFile',
            fields=[
                ('id', models.AutoField(primary_key=True, auto_created=True, serialize=False, verbose_name='ID')),
                ('submitted_file', models.FileField(upload_to=autograder.models.submission._get_submission_file_upload_to_dir, max_length=510, validators=[autograder.models.submission._validate_filename])),
            ],
            options={
                'abstract': False,
            },
        ),
        migrations.CreateModel(
            name='_UploadedProjectFile',
            fields=[
                ('id', models.AutoField(primary_key=True, auto_created=True, serialize=False, verbose_name='ID')),
                ('uploaded_file', models.FileField(upload_to=autograder.models.project._get_project_file_upload_to_dir, max_length=510, validators=[autograder.models.project._validate_filename])),
            ],
            options={
                'abstract': False,
            },
        ),
        migrations.CreateModel(
            name='AutograderTestCaseResultBase',
            fields=[
                ('id', models.AutoField(primary_key=True, auto_created=True, serialize=False, verbose_name='ID')),
                ('return_code', models.IntegerField(default=None, null=True)),
                ('standard_output', models.TextField()),
                ('standard_error_output', models.TextField()),
                ('timed_out', models.BooleanField(default=False)),
                ('valgrind_return_code', models.IntegerField(default=None, null=True)),
                ('valgrind_output', models.TextField()),
                ('compilation_return_code', models.IntegerField(default=None, null=True)),
                ('compilation_standard_output', models.TextField()),
                ('compilation_standard_error_output', models.TextField()),
                ('polymorphic_ctype', models.ForeignKey(to='contenttypes.ContentType', null=True, related_name='polymorphic_autograder.autogradertestcaseresultbase_set+', editable=False)),
            ],
            options={
                'abstract': False,
            },
        ),
        migrations.CreateModel(
            name='Course',
            fields=[
                ('id', models.AutoField(primary_key=True, auto_created=True, serialize=False, verbose_name='ID')),
                ('name', models.CharField(unique=True, max_length=255)),
                ('_course_admin_names', django.contrib.postgres.fields.ArrayField(base_field=models.CharField(max_length=255), default=list, blank=True, size=None)),
            ],
            options={
                'abstract': False,
            },
        ),
        migrations.CreateModel(
            name='PolymorphicModelValidatableOnSave',
            fields=[
                ('id', models.AutoField(primary_key=True, auto_created=True, serialize=False, verbose_name='ID')),
            ],
            options={
                'abstract': False,
            },
        ),
        migrations.CreateModel(
            name='Project',
            fields=[
                ('id', models.AutoField(primary_key=True, auto_created=True, serialize=False, verbose_name='ID')),
                ('name', models.CharField(max_length=255)),
                ('test_case_feedback_configuration', autograder.models.fields.FeedbackConfigurationField(default=autograder.models.fields.FeedbackConfiguration)),
                ('visible_to_students', models.BooleanField(default=False)),
                ('closing_time', models.DateTimeField(default=None, blank=True, null=True)),
                ('disallow_student_submissions', models.BooleanField(default=False)),
                ('allow_submissions_from_non_enrolled_students', models.BooleanField(default=False)),
                ('min_group_size', models.IntegerField(default=1, validators=[django.core.validators.MinValueValidator(1)])),
                ('max_group_size', models.IntegerField(default=1, validators=[django.core.validators.MinValueValidator(1)])),
                ('_required_student_files', django.contrib.postgres.fields.ArrayField(base_field=models.CharField(blank=True, max_length=255), default=list, blank=True, size=None)),
                ('_expected_student_file_patterns', jsonfield.fields.JSONField(default=list, blank=True)),
            ],
        ),
        migrations.CreateModel(
            name='Semester',
            fields=[
                ('id', models.AutoField(primary_key=True, auto_created=True, serialize=False, verbose_name='ID')),
                ('name', models.CharField(max_length=255)),
                ('_semester_staff_names', django.contrib.postgres.fields.ArrayField(base_field=models.CharField(max_length=255), default=list, blank=True, size=None)),
                ('_enrolled_student_names', django.contrib.postgres.fields.ArrayField(base_field=models.CharField(max_length=255), default=list, blank=True, size=None)),
                ('course', models.ForeignKey(to='autograder.Course', related_name='semesters')),
            ],
        ),
        migrations.CreateModel(
            name='StudentTestSuiteResult',
            fields=[
                ('id', models.AutoField(primary_key=True, auto_created=True, serialize=False, verbose_name='ID')),
                ('blah', autograder.models.fields.ClassField(class_=autograder.models.student_test_suite.student_test_suite_result.StudentTestCaseEvaluationResult, editable=False)),
            ],
        ),
        migrations.CreateModel(
            name='Submission',
            fields=[
                ('id', models.AutoField(primary_key=True, auto_created=True, serialize=False, verbose_name='ID')),
                ('discarded_files', django.contrib.postgres.fields.ArrayField(base_field=models.CharField(max_length=255), default=list, blank=True, size=None)),
                ('_timestamp', models.DateTimeField(auto_now_add=True)),
                ('test_case_feedback_config_override', autograder.models.fields.FeedbackConfigurationField(default=None, null=True)),
                ('show_all_test_cases', models.BooleanField(default=False)),
                ('status', models.CharField(choices=[('received', 'Received'), ('queued', 'Queued'), ('being_graded', 'Being graded'), ('finished_grading', 'Finished grading'), ('invalid', 'Invalid'), ('error', 'Error')], default='received', max_length=255)),
                ('invalid_reason_or_error', jsonfield.fields.JSONField(default=list)),
            ],
            options={
                'abstract': False,
            },
        ),
        migrations.CreateModel(
            name='SubmissionGroup',
            fields=[
                ('id', models.AutoField(primary_key=True, auto_created=True, serialize=False, verbose_name='ID')),
                ('_members', django.contrib.postgres.fields.ArrayField(base_field=models.CharField(max_length=30), size=None)),
                ('extended_due_date', models.DateTimeField(default=None, blank=True, null=True)),
                ('project', models.ForeignKey(to='autograder.Project', related_name='submission_groups')),
            ],
            options={
                'abstract': False,
            },
        ),
        migrations.CreateModel(
            name='AutograderTestCaseBase',
            fields=[
                ('polymorphicmodelvalidatableonsave_ptr', models.OneToOneField(primary_key=True, serialize=False, auto_created=True, parent_link=True, to='autograder.PolymorphicModelValidatableOnSave')),
                ('name', models.CharField(max_length=255)),
                ('hide_from_students', models.BooleanField(default=True)),
                ('command_line_arguments', django.contrib.postgres.fields.ArrayField(base_field=models.CharField(blank=True, max_length=255), default=list, blank=True, size=None)),
                ('standard_input', models.TextField(blank=True)),
                ('test_resource_files', django.contrib.postgres.fields.ArrayField(base_field=models.CharField(max_length=255), default=list, blank=True, size=None)),
                ('student_resource_files', django.contrib.postgres.fields.ArrayField(base_field=models.CharField(max_length=255), default=list, blank=True, size=None)),
                ('time_limit', models.IntegerField(default=10, validators=[django.core.validators.MinValueValidator(1)])),
                ('expected_return_code', models.IntegerField(default=None, blank=True, null=True)),
                ('expect_any_nonzero_return_code', models.BooleanField(default=False)),
                ('expected_standard_output', models.TextField(blank=True)),
                ('expected_standard_error_output', models.TextField(blank=True)),
                ('_use_valgrind', models.BooleanField(default=False)),
                ('valgrind_flags', django.contrib.postgres.fields.ArrayField(base_field=models.CharField(blank=True, max_length=255), default=None, blank=True, null=True, size=None)),
                ('points_for_correct_return_code', models.IntegerField(default=0, validators=[django.core.validators.MinValueValidator(0)])),
                ('points_for_correct_output', models.IntegerField(default=0, validators=[django.core.validators.MinValueValidator(0)])),
                ('points_for_no_valgrind_errors', models.IntegerField(default=0, validators=[django.core.validators.MinValueValidator(0)])),
                ('points_for_compilation_success', models.IntegerField(default=0, validators=[django.core.validators.MinValueValidator(0)])),
                ('compiler', models.CharField(blank=True, max_length=255)),
                ('compiler_flags', django.contrib.postgres.fields.ArrayField(base_field=models.CharField(blank=True, max_length=255), default=list, blank=True, size=None)),
                ('files_to_compile_together', django.contrib.postgres.fields.ArrayField(base_field=models.CharField(max_length=255), default=list, blank=True, size=None)),
                ('executable_name', models.CharField(blank=True, max_length=255)),
            ],
            bases=('autograder.polymorphicmodelvalidatableonsave',),
        ),
        migrations.CreateModel(
            name='StudentTestSuiteBase',
            fields=[
                ('polymorphicmodelvalidatableonsave_ptr', models.OneToOneField(primary_key=True, serialize=False, auto_created=True, parent_link=True, to='autograder.PolymorphicModelValidatableOnSave')),
                ('name', models.CharField(max_length=255)),
                ('student_test_case_filename_pattern', models.CharField(max_length=255)),
                ('correct_implementation_filename', models.CharField(max_length=255)),
                ('buggy_implementation_filenames', django.contrib.postgres.fields.ArrayField(base_field=models.CharField(blank=True, max_length=255), default=list, blank=True, size=None)),
                ('implementation_file_alias', models.CharField(blank=True, max_length=255)),
                ('suite_resource_filenames', django.contrib.postgres.fields.ArrayField(base_field=models.CharField(blank=True, max_length=255), default=list, blank=True, size=None)),
                ('time_limit', models.IntegerField(default=10, validators=[django.core.validators.MinValueValidator(1), django.core.validators.MaxValueValidator(60)])),
                ('hide_from_students', models.BooleanField(default=True)),
                ('compiler', models.CharField(choices=[('g++', 'g++')], default='g++', max_length=255)),
                ('compiler_flags', autograder.models.fields.StringListField(default=list, blank=True, size=None)),
                ('suite_resource_files_to_compile_together', autograder.models.fields.StringListField(default=list, blank=True, size=None)),
            ],
            bases=('autograder.polymorphicmodelvalidatableonsave',),
        ),
        migrations.AddField(
            model_name='submission',
            name='submission_group',
            field=models.ForeignKey(to='autograder.SubmissionGroup', related_name='submissions'),
        ),
        migrations.AddField(
            model_name='project',
            name='semester',
            field=models.ForeignKey(to='autograder.Semester', related_name='projects'),
        ),
        migrations.AddField(
            model_name='polymorphicmodelvalidatableonsave',
            name='polymorphic_ctype',
            field=models.ForeignKey(to='contenttypes.ContentType', null=True, related_name='polymorphic_autograder.polymorphicmodelvalidatableonsave_set+', editable=False),
        ),
        migrations.AddField(
            model_name='autogradertestcaseresultbase',
            name='submission',
            field=models.ForeignKey(default=None, null=True, related_name='results', blank=True, to='autograder.Submission'),
        ),
        migrations.AddField(
            model_name='_uploadedprojectfile',
            name='project',
            field=models.ForeignKey(to='autograder.Project', related_name='_project_files'),
        ),
        migrations.AddField(
            model_name='_submittedfile',
            name='submission',
            field=models.ForeignKey(to='autograder.Submission', related_name='_submitted_files'),
        ),
        migrations.CreateModel(
            name='CompilationOnlyAutograderTestCase',
            fields=[
                ('autogradertestcasebase_ptr', models.OneToOneField(primary_key=True, serialize=False, auto_created=True, parent_link=True, to='autograder.AutograderTestCaseBase')),
            ],
            options={
                'abstract': False,
            },
            bases=('autograder.autogradertestcasebase',),
        ),
        migrations.CreateModel(
            name='CompiledAutograderTestCase',
            fields=[
                ('autogradertestcasebase_ptr', models.OneToOneField(primary_key=True, serialize=False, auto_created=True, parent_link=True, to='autograder.AutograderTestCaseBase')),
            ],
            options={
                'abstract': False,
            },
            bases=('autograder.autogradertestcasebase',),
        ),
        migrations.CreateModel(
            name='CompiledStudentTestSuite',
            fields=[
                ('studenttestsuitebase_ptr', models.OneToOneField(primary_key=True, serialize=False, auto_created=True, parent_link=True, to='autograder.StudentTestSuiteBase')),
            ],
            options={
                'abstract': False,
            },
            bases=('autograder.studenttestsuitebase',),
        ),
        migrations.AddField(
            model_name='studenttestsuitebase',
            name='project',
            field=models.ForeignKey(to='autograder.Project', related_name='student_test_suites'),
        ),
        migrations.AlterUniqueTogether(
            name='semester',
            unique_together=set([('name', 'course')]),
        ),
        migrations.AlterUniqueTogether(
            name='project',
            unique_together=set([('name', 'semester')]),
        ),
        migrations.AddField(
            model_name='autogradertestcaseresultbase',
            name='test_case',
            field=models.ForeignKey(to='autograder.AutograderTestCaseBase'),
        ),
        migrations.AddField(
            model_name='autogradertestcasebase',
            name='project',
            field=models.ForeignKey(to='autograder.Project', related_name='autograder_test_cases'),
        ),
        migrations.AlterUniqueTogether(
            name='studenttestsuitebase',
            unique_together=set([('name', 'project')]),
        ),
        migrations.AlterUniqueTogether(
            name='autogradertestcasebase',
            unique_together=set([('name', 'project')]),
        ),
    ]
