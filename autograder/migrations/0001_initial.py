# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations
import django.contrib.postgres.fields
from django.conf import settings
import jsonfield.fields
import django.core.validators
import autograder.models.submission
import autograder.models.project
import autograder.models.fields


class Migration(migrations.Migration):

    dependencies = [
        ('contenttypes', '0002_remove_content_type_name'),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name='_SubmittedFile',
            fields=[
                ('id', models.AutoField(primary_key=True, serialize=False, verbose_name='ID', auto_created=True)),
                ('submitted_file', models.FileField(max_length=510, upload_to=autograder.models.submission._get_submission_file_upload_to_dir, validators=[autograder.models.submission._validate_filename])),
            ],
            options={
                'abstract': False,
            },
        ),
        migrations.CreateModel(
            name='_UploadedProjectFile',
            fields=[
                ('id', models.AutoField(primary_key=True, serialize=False, verbose_name='ID', auto_created=True)),
                ('uploaded_file', models.FileField(max_length=510, upload_to=autograder.models.project._get_project_file_upload_to_dir, validators=[autograder.models.project._validate_filename])),
            ],
            options={
                'abstract': False,
            },
        ),
        migrations.CreateModel(
            name='AutograderTestCaseResultBase',
            fields=[
                ('id', models.AutoField(primary_key=True, serialize=False, verbose_name='ID', auto_created=True)),
                ('_return_code', models.IntegerField(default=None, null=True)),
                ('_standard_output', models.TextField()),
                ('_standard_error_output', models.TextField()),
                ('_timed_out', models.BooleanField(default=False)),
                ('_valgrind_return_code', models.IntegerField(default=None, null=True)),
                ('_valgrind_output', models.TextField()),
                ('_compilation_return_code', models.IntegerField(default=None, null=True)),
                ('_compilation_standard_output', models.TextField()),
                ('_compilation_standard_error_output', models.TextField()),
            ],
            options={
                'abstract': False,
            },
        ),
        migrations.CreateModel(
            name='Course',
            fields=[
                ('id', models.AutoField(primary_key=True, serialize=False, verbose_name='ID', auto_created=True)),
                ('name', models.CharField(max_length=255, unique=True)),
                ('_course_admin_names', django.contrib.postgres.fields.ArrayField(blank=True, default=list, base_field=models.CharField(max_length=255), size=None)),
            ],
            options={
                'abstract': False,
            },
        ),
        migrations.CreateModel(
            name='PolymorphicModelValidatableOnSave',
            fields=[
                ('id', models.AutoField(primary_key=True, serialize=False, verbose_name='ID', auto_created=True)),
            ],
            options={
                'abstract': False,
            },
        ),
        migrations.CreateModel(
            name='Project',
            fields=[
                ('id', models.AutoField(primary_key=True, serialize=False, verbose_name='ID', auto_created=True)),
                ('name', models.CharField(max_length=255)),
                ('test_case_feedback_configuration', autograder.models.fields.FeedbackConfigurationField(default=autograder.models.fields.FeedbackConfiguration)),
                ('visible_to_students', models.BooleanField(default=False)),
                ('closing_time', models.DateTimeField(blank=True, default=None, null=True)),
                ('disallow_student_submissions', models.BooleanField(default=False)),
                ('allow_submissions_from_non_enrolled_students', models.BooleanField(default=False)),
                ('min_group_size', models.IntegerField(default=1, validators=[django.core.validators.MinValueValidator(1)])),
                ('max_group_size', models.IntegerField(default=1, validators=[django.core.validators.MinValueValidator(1)])),
                ('required_student_files', django.contrib.postgres.fields.ArrayField(blank=True, default=list, base_field=models.CharField(max_length=255, blank=True), size=None)),
                ('_expected_student_file_patterns', jsonfield.fields.JSONField(blank=True, default=list)),
            ],
        ),
        migrations.CreateModel(
            name='Semester',
            fields=[
                ('id', models.AutoField(primary_key=True, serialize=False, verbose_name='ID', auto_created=True)),
                ('name', models.CharField(max_length=255)),
                ('_semester_staff_names', django.contrib.postgres.fields.ArrayField(blank=True, default=list, base_field=models.CharField(max_length=255), size=None)),
                ('_enrolled_student_names', django.contrib.postgres.fields.ArrayField(blank=True, default=list, base_field=models.CharField(max_length=255), size=None)),
                ('course', models.ForeignKey(related_name='semesters', to='autograder.Course')),
            ],
        ),
        migrations.CreateModel(
            name='Submission',
            fields=[
                ('id', models.AutoField(primary_key=True, serialize=False, verbose_name='ID', auto_created=True)),
                ('_timestamp', models.DateTimeField(auto_now_add=True)),
                ('test_case_feedback_config_override', autograder.models.fields.FeedbackConfigurationField(default=None, null=True)),
                ('status', models.CharField(max_length=255, default='received', choices=[('received', 'Received'), ('queued', 'Queued'), ('being_graded', 'Being graded'), ('finished_grading', 'Finished grading'), ('invalid', 'Invalid')])),
                ('invalid_reason', jsonfield.fields.JSONField(default=[])),
            ],
        ),
        migrations.CreateModel(
            name='SubmissionGroup',
            fields=[
                ('id', models.AutoField(primary_key=True, serialize=False, verbose_name='ID', auto_created=True)),
                ('extended_due_date', models.DateTimeField(blank=True, default=None, null=True)),
                ('members', models.ManyToManyField(related_name='submission_groups', to=settings.AUTH_USER_MODEL)),
                ('project', models.ForeignKey(to='autograder.Project')),
            ],
            options={
                'abstract': False,
            },
        ),
        migrations.CreateModel(
            name='AutograderTestCaseBase',
            fields=[
                ('polymorphicmodelvalidatableonsave_ptr', models.OneToOneField(auto_created=True, parent_link=True, primary_key=True, to='autograder.PolymorphicModelValidatableOnSave', serialize=False)),
                ('name', models.CharField(max_length=255)),
                ('hide_from_students', models.BooleanField(default=True)),
                ('command_line_arguments', django.contrib.postgres.fields.ArrayField(blank=True, default=list, base_field=models.CharField(max_length=255, blank=True), size=None)),
                ('standard_input', models.TextField(blank=True)),
                ('test_resource_files', django.contrib.postgres.fields.ArrayField(blank=True, default=list, base_field=models.CharField(max_length=255), size=None)),
                ('time_limit', models.IntegerField(default=10, validators=[django.core.validators.MinValueValidator(1)])),
                ('expected_return_code', models.IntegerField(blank=True, default=None, null=True)),
                ('expect_any_nonzero_return_code', models.BooleanField(default=False)),
                ('expected_standard_output', models.TextField(blank=True)),
                ('expected_standard_error_output', models.TextField(blank=True)),
                ('_use_valgrind', models.BooleanField(default=False)),
                ('valgrind_flags', django.contrib.postgres.fields.ArrayField(blank=True, default=None, base_field=models.CharField(max_length=255, blank=True), size=None, null=True)),
                ('points_for_correct_return_code', models.IntegerField(default=0, validators=[django.core.validators.MinValueValidator(0)])),
                ('points_for_correct_output', models.IntegerField(default=0, validators=[django.core.validators.MinValueValidator(0)])),
                ('points_for_no_valgrind_errors', models.IntegerField(default=0, validators=[django.core.validators.MinValueValidator(0)])),
                ('points_for_compilation_success', models.IntegerField(default=0, validators=[django.core.validators.MinValueValidator(0)])),
                ('compiler', models.CharField(max_length=255, blank=True)),
                ('compiler_flags', django.contrib.postgres.fields.ArrayField(blank=True, default=list, base_field=models.CharField(max_length=255, blank=True), size=None)),
                ('files_to_compile_together', django.contrib.postgres.fields.ArrayField(blank=True, default=list, base_field=models.CharField(max_length=255), size=None)),
                ('executable_name', models.CharField(max_length=255, blank=True)),
            ],
            bases=('autograder.polymorphicmodelvalidatableonsave',),
        ),
        migrations.CreateModel(
            name='CompiledAutograderTestCaseResult',
            fields=[
                ('autogradertestcaseresultbase_ptr', models.OneToOneField(auto_created=True, parent_link=True, primary_key=True, to='autograder.AutograderTestCaseResultBase', serialize=False)),
            ],
            options={
                'abstract': False,
            },
            bases=('autograder.autogradertestcaseresultbase',),
        ),
        migrations.AddField(
            model_name='submission',
            name='submission_group',
            field=models.ForeignKey(to='autograder.SubmissionGroup'),
        ),
        migrations.AddField(
            model_name='project',
            name='semester',
            field=models.ForeignKey(related_name='projects', to='autograder.Semester'),
        ),
        migrations.AddField(
            model_name='polymorphicmodelvalidatableonsave',
            name='polymorphic_ctype',
            field=models.ForeignKey(related_name='polymorphic_autograder.polymorphicmodelvalidatableonsave_set+', editable=False, to='contenttypes.ContentType', null=True),
        ),
        migrations.AddField(
            model_name='autogradertestcaseresultbase',
            name='polymorphic_ctype',
            field=models.ForeignKey(related_name='polymorphic_autograder.autogradertestcaseresultbase_set+', editable=False, to='contenttypes.ContentType', null=True),
        ),
        migrations.AddField(
            model_name='_uploadedprojectfile',
            name='project',
            field=models.ForeignKey(related_name='_project_files', to='autograder.Project'),
        ),
        migrations.AddField(
            model_name='_submittedfile',
            name='submission',
            field=models.ForeignKey(related_name='submitted_files', to='autograder.Submission'),
        ),
        migrations.CreateModel(
            name='CompiledAutograderTestCase',
            fields=[
                ('autogradertestcasebase_ptr', models.OneToOneField(auto_created=True, parent_link=True, primary_key=True, to='autograder.AutograderTestCaseBase', serialize=False)),
            ],
            options={
                'abstract': False,
            },
            bases=('autograder.autogradertestcasebase',),
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
            field=models.ForeignKey(related_name='autograder_test_cases', to='autograder.Project'),
        ),
        migrations.AlterUniqueTogether(
            name='autogradertestcasebase',
            unique_together=set([('name', 'project')]),
        ),
    ]
