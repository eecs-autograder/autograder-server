# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations
import autograder.models.project
import django.contrib.postgres.fields
import autograder.models.fields
import django.core.validators
import autograder.models.submission
import jsonfield.fields
from django.conf import settings


class Migration(migrations.Migration):

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ('contenttypes', '0002_remove_content_type_name'),
    ]

    operations = [
        migrations.CreateModel(
            name='_SubmittedFile',
            fields=[
                ('id', models.AutoField(serialize=False, auto_created=True, primary_key=True, verbose_name='ID')),
                ('submitted_file', models.FileField(max_length=510, validators=[autograder.models.submission._validate_filename], upload_to=autograder.models.submission._get_submission_file_upload_to_dir)),
            ],
        ),
        migrations.CreateModel(
            name='AutograderTestCaseResultBase',
            fields=[
                ('id', models.AutoField(serialize=False, auto_created=True, primary_key=True, verbose_name='ID')),
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
            name='ModelValidatableOnSave',
            fields=[
                ('id', models.AutoField(serialize=False, auto_created=True, primary_key=True, verbose_name='ID')),
            ],
        ),
        migrations.CreateModel(
            name='PolymorphicModelValidatableOnSave',
            fields=[
                ('id', models.AutoField(serialize=False, auto_created=True, primary_key=True, verbose_name='ID')),
            ],
            options={
                'abstract': False,
            },
        ),
        migrations.CreateModel(
            name='_UploadedProjectFile',
            fields=[
                ('modelvalidatableonsave_ptr', models.OneToOneField(primary_key=True, to='autograder.ModelValidatableOnSave', auto_created=True, serialize=False, parent_link=True)),
                ('uploaded_file', models.FileField(max_length=510, validators=[autograder.models.project._validate_filename], upload_to=autograder.models.project._get_project_file_upload_to_dir)),
            ],
            bases=('autograder.modelvalidatableonsave',),
        ),
        migrations.CreateModel(
            name='AutograderTestCaseBase',
            fields=[
                ('polymorphicmodelvalidatableonsave_ptr', models.OneToOneField(primary_key=True, to='autograder.PolymorphicModelValidatableOnSave', auto_created=True, serialize=False, parent_link=True)),
                ('name', models.CharField(max_length=255)),
                ('hide_from_students', models.BooleanField(default=True)),
                ('command_line_arguments', django.contrib.postgres.fields.ArrayField(default=list, base_field=models.CharField(max_length=255, blank=True), blank=True, size=None)),
                ('standard_input', models.TextField(blank=True)),
                ('test_resource_files', django.contrib.postgres.fields.ArrayField(default=list, base_field=models.CharField(max_length=255), blank=True, size=None)),
                ('time_limit', models.IntegerField(default=10, validators=[django.core.validators.MinValueValidator(1)])),
                ('expected_return_code', models.IntegerField(default=None, null=True, blank=True)),
                ('expect_any_nonzero_return_code', models.BooleanField(default=False)),
                ('expected_standard_output', models.TextField(blank=True)),
                ('expected_standard_error_output', models.TextField(blank=True)),
                ('_use_valgrind', models.BooleanField(default=False)),
                ('valgrind_flags', django.contrib.postgres.fields.ArrayField(default=None, null=True, base_field=models.CharField(max_length=255, blank=True), blank=True, size=None)),
                ('points_for_correct_return_code', models.IntegerField(default=0, validators=[django.core.validators.MinValueValidator(0)])),
                ('points_for_correct_output', models.IntegerField(default=0, validators=[django.core.validators.MinValueValidator(0)])),
                ('points_for_no_valgrind_errors', models.IntegerField(default=0, validators=[django.core.validators.MinValueValidator(0)])),
                ('points_for_compilation_success', models.IntegerField(default=0, validators=[django.core.validators.MinValueValidator(0)])),
                ('compiler', models.CharField(max_length=255, blank=True)),
                ('compiler_flags', django.contrib.postgres.fields.ArrayField(default=list, base_field=models.CharField(max_length=255, blank=True), blank=True, size=None)),
                ('files_to_compile_together', django.contrib.postgres.fields.ArrayField(default=list, base_field=models.CharField(max_length=255), blank=True, size=None)),
                ('executable_name', models.CharField(max_length=255, blank=True)),
            ],
            bases=('autograder.polymorphicmodelvalidatableonsave',),
        ),
        migrations.CreateModel(
            name='CompiledAutograderTestCaseResult',
            fields=[
                ('autogradertestcaseresultbase_ptr', models.OneToOneField(primary_key=True, to='autograder.AutograderTestCaseResultBase', auto_created=True, serialize=False, parent_link=True)),
            ],
            options={
                'abstract': False,
            },
            bases=('autograder.autogradertestcaseresultbase',),
        ),
        migrations.CreateModel(
            name='Course',
            fields=[
                ('modelvalidatableonsave_ptr', models.OneToOneField(primary_key=True, to='autograder.ModelValidatableOnSave', auto_created=True, serialize=False, parent_link=True)),
                ('name', models.CharField(max_length=255, unique=True)),
                ('_course_admin_names', django.contrib.postgres.fields.ArrayField(default=list, base_field=models.CharField(max_length=255), blank=True, size=None)),
            ],
            bases=('autograder.modelvalidatableonsave',),
        ),
        migrations.CreateModel(
            name='Project',
            fields=[
                ('modelvalidatableonsave_ptr', models.OneToOneField(primary_key=True, to='autograder.ModelValidatableOnSave', auto_created=True, serialize=False, parent_link=True)),
                ('name', models.CharField(max_length=255)),
                ('test_case_feedback_configuration', autograder.models.fields.FeedbackConfigurationField(default=autograder.models.fields.FeedbackConfiguration, validators=[autograder.models.fields._validate_feedback_configuration, autograder.models.fields._validate_feedback_configuration, autograder.models.fields._validate_feedback_configuration, autograder.models.fields._validate_feedback_configuration, autograder.models.fields._validate_feedback_configuration])),
                ('visible_to_students', models.BooleanField(default=False)),
                ('closing_time', models.DateTimeField(default=None, null=True, blank=True)),
                ('disallow_student_submissions', models.BooleanField(default=False)),
                ('allow_submissions_from_non_enrolled_students', models.BooleanField(default=False)),
                ('min_group_size', models.IntegerField(default=1, validators=[django.core.validators.MinValueValidator(1)])),
                ('max_group_size', models.IntegerField(default=1, validators=[django.core.validators.MinValueValidator(1)])),
                ('required_student_files', django.contrib.postgres.fields.ArrayField(default=list, base_field=models.CharField(max_length=255, blank=True), blank=True, size=None)),
                ('_expected_student_file_patterns', jsonfield.fields.JSONField(default=list, blank=True)),
            ],
            bases=('autograder.modelvalidatableonsave',),
        ),
        migrations.CreateModel(
            name='Semester',
            fields=[
                ('modelvalidatableonsave_ptr', models.OneToOneField(primary_key=True, to='autograder.ModelValidatableOnSave', auto_created=True, serialize=False, parent_link=True)),
                ('name', models.CharField(max_length=255)),
                ('_semester_staff_names', django.contrib.postgres.fields.ArrayField(default=list, base_field=models.CharField(max_length=255), blank=True, size=None)),
                ('_enrolled_student_names', django.contrib.postgres.fields.ArrayField(default=list, base_field=models.CharField(max_length=255), blank=True, size=None)),
                ('course', models.ForeignKey(to='autograder.Course', related_name='semesters')),
            ],
            bases=('autograder.modelvalidatableonsave',),
        ),
        migrations.CreateModel(
            name='Submission',
            fields=[
                ('modelvalidatableonsave_ptr', models.OneToOneField(primary_key=True, to='autograder.ModelValidatableOnSave', auto_created=True, serialize=False, parent_link=True)),
                ('ignore_extra_files', models.BooleanField(default=True)),
                ('_timestamp', models.DateTimeField(auto_now_add=True)),
            ],
            bases=('autograder.modelvalidatableonsave',),
        ),
        migrations.CreateModel(
            name='SubmissionGroup',
            fields=[
                ('modelvalidatableonsave_ptr', models.OneToOneField(primary_key=True, to='autograder.ModelValidatableOnSave', auto_created=True, serialize=False, parent_link=True)),
                ('extended_due_date', models.DateTimeField(default=None, null=True, blank=True)),
                ('members', models.ManyToManyField(to=settings.AUTH_USER_MODEL, related_name='submission_groups')),
                ('project', models.ForeignKey(to='autograder.Project')),
            ],
            bases=('autograder.modelvalidatableonsave',),
        ),
        migrations.AddField(
            model_name='polymorphicmodelvalidatableonsave',
            name='polymorphic_ctype',
            field=models.ForeignKey(null=True, related_name='polymorphic_autograder.polymorphicmodelvalidatableonsave_set+', to='contenttypes.ContentType', editable=False),
        ),
        migrations.AddField(
            model_name='autogradertestcaseresultbase',
            name='polymorphic_ctype',
            field=models.ForeignKey(null=True, related_name='polymorphic_autograder.autogradertestcaseresultbase_set+', to='contenttypes.ContentType', editable=False),
        ),
        migrations.CreateModel(
            name='CompiledAutograderTestCase',
            fields=[
                ('autogradertestcasebase_ptr', models.OneToOneField(primary_key=True, to='autograder.AutograderTestCaseBase', auto_created=True, serialize=False, parent_link=True)),
            ],
            options={
                'abstract': False,
            },
            bases=('autograder.autogradertestcasebase',),
        ),
        migrations.AddField(
            model_name='submission',
            name='submission_group',
            field=models.ForeignKey(to='autograder.SubmissionGroup'),
        ),
        migrations.AddField(
            model_name='project',
            name='semester',
            field=models.ForeignKey(to='autograder.Semester', related_name='projects'),
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
        migrations.AddField(
            model_name='_uploadedprojectfile',
            name='project',
            field=models.ForeignKey(to='autograder.Project', related_name='_project_files'),
        ),
        migrations.AddField(
            model_name='_submittedfile',
            name='submission',
            field=models.ForeignKey(to='autograder.Submission', related_name='submitted_files'),
        ),
        migrations.AlterUniqueTogether(
            name='semester',
            unique_together=set([('name', 'course')]),
        ),
        migrations.AlterUniqueTogether(
            name='project',
            unique_together=set([('name', 'semester')]),
        ),
        migrations.AlterUniqueTogether(
            name='autogradertestcasebase',
            unique_together=set([('name', 'project')]),
        ),
    ]
