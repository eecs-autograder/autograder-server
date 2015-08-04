# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations
import autograder.models.submission
import autograder.models.project
import django.core.validators
import django.contrib.postgres.fields
from django.conf import settings
import jsonfield.fields


class Migration(migrations.Migration):

    dependencies = [
        ('contenttypes', '0002_remove_content_type_name'),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name='_SubmittedFile',
            fields=[
                ('id', models.AutoField(verbose_name='ID', primary_key=True, serialize=False, auto_created=True)),
                ('submitted_file', models.FileField(max_length=510, upload_to=autograder.models.submission._get_submission_file_upload_to_dir, validators=[autograder.models.submission._validate_filename])),
            ],
        ),
        migrations.CreateModel(
            name='AutograderTestCaseBase',
            fields=[
                ('id', models.AutoField(verbose_name='ID', primary_key=True, serialize=False, auto_created=True)),
                ('name', models.CharField(max_length=255)),
                ('command_line_arguments', django.contrib.postgres.fields.ArrayField(base_field=models.CharField(blank=True, max_length=255), blank=True, size=None, default=list)),
                ('standard_input', models.TextField(blank=True)),
                ('test_resource_files', django.contrib.postgres.fields.ArrayField(base_field=models.CharField(max_length=255), blank=True, size=None, default=list)),
                ('time_limit', models.IntegerField(default=10, validators=[django.core.validators.MinValueValidator(1)])),
                ('expected_return_code', models.IntegerField(null=True, blank=True, default=None)),
                ('expect_any_nonzero_return_code', models.BooleanField(default=False)),
                ('expected_standard_output', models.TextField(blank=True)),
                ('expected_standard_error_output', models.TextField(blank=True)),
                ('_use_valgrind', models.BooleanField(default=False)),
                ('valgrind_flags', django.contrib.postgres.fields.ArrayField(base_field=models.CharField(blank=True, max_length=255), null=True, blank=True, size=None, default=None)),
                ('compiler', models.CharField(blank=True, max_length=255)),
                ('compiler_flags', django.contrib.postgres.fields.ArrayField(base_field=models.CharField(blank=True, max_length=255), blank=True, size=None, default=list)),
                ('files_to_compile_together', django.contrib.postgres.fields.ArrayField(base_field=models.CharField(max_length=255), blank=True, size=None, default=list)),
                ('executable_name', models.CharField(blank=True, max_length=255)),
            ],
        ),
        migrations.CreateModel(
            name='AutograderTestCaseResultBase',
            fields=[
                ('id', models.AutoField(verbose_name='ID', primary_key=True, serialize=False, auto_created=True)),
                ('_return_code', models.IntegerField(null=True, default=None)),
                ('_standard_output', models.TextField()),
                ('_standard_error_output', models.TextField()),
                ('_timed_out', models.BooleanField(default=False)),
                ('_valgrind_return_code', models.IntegerField(null=True, default=None)),
                ('_valgrind_output', models.TextField()),
                ('_compilation_return_code', models.IntegerField(null=True, default=None)),
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
                ('id', models.AutoField(verbose_name='ID', primary_key=True, serialize=False, auto_created=True)),
            ],
        ),
        migrations.CreateModel(
            name='_UploadedProjectFile',
            fields=[
                ('modelvalidatableonsave_ptr', models.OneToOneField(parent_link=True, auto_created=True, serialize=False, primary_key=True, to='autograder.ModelValidatableOnSave')),
                ('uploaded_file', models.FileField(max_length=510, upload_to=autograder.models.project._get_project_file_upload_to_dir, validators=[autograder.models.project._validate_filename])),
            ],
            bases=('autograder.modelvalidatableonsave',),
        ),
        migrations.CreateModel(
            name='CompiledAutograderTestCase',
            fields=[
                ('autogradertestcasebase_ptr', models.OneToOneField(parent_link=True, auto_created=True, serialize=False, primary_key=True, to='autograder.AutograderTestCaseBase')),
            ],
            options={
                'abstract': False,
            },
            bases=('autograder.autogradertestcasebase',),
        ),
        migrations.CreateModel(
            name='CompiledAutograderTestCaseResult',
            fields=[
                ('autogradertestcaseresultbase_ptr', models.OneToOneField(parent_link=True, auto_created=True, serialize=False, primary_key=True, to='autograder.AutograderTestCaseResultBase')),
            ],
            options={
                'abstract': False,
            },
            bases=('autograder.autogradertestcaseresultbase',),
        ),
        migrations.CreateModel(
            name='Course',
            fields=[
                ('modelvalidatableonsave_ptr', models.OneToOneField(parent_link=True, auto_created=True, serialize=False, primary_key=True, to='autograder.ModelValidatableOnSave')),
                ('name', models.CharField(unique=True, max_length=255)),
                ('_course_admin_names', django.contrib.postgres.fields.ArrayField(base_field=models.CharField(max_length=255), blank=True, size=None, default=list)),
            ],
            bases=('autograder.modelvalidatableonsave',),
        ),
        migrations.CreateModel(
            name='Project',
            fields=[
                ('modelvalidatableonsave_ptr', models.OneToOneField(parent_link=True, auto_created=True, serialize=False, primary_key=True, to='autograder.ModelValidatableOnSave')),
                ('name', models.CharField(max_length=255)),
                ('visible_to_students', models.BooleanField(default=False)),
                ('closing_time', models.DateTimeField(null=True, blank=True, default=None)),
                ('disallow_student_submissions', models.BooleanField(default=False)),
                ('min_group_size', models.IntegerField(default=1, validators=[django.core.validators.MinValueValidator(1)])),
                ('max_group_size', models.IntegerField(default=1, validators=[django.core.validators.MinValueValidator(1)])),
                ('required_student_files', django.contrib.postgres.fields.ArrayField(base_field=models.CharField(blank=True, max_length=255), blank=True, size=None, default=list)),
                ('_expected_student_file_patterns', jsonfield.fields.JSONField(blank=True, default=list)),
            ],
            bases=('autograder.modelvalidatableonsave',),
        ),
        migrations.CreateModel(
            name='Semester',
            fields=[
                ('modelvalidatableonsave_ptr', models.OneToOneField(parent_link=True, auto_created=True, serialize=False, primary_key=True, to='autograder.ModelValidatableOnSave')),
                ('name', models.CharField(max_length=255)),
                ('_semester_staff_names', django.contrib.postgres.fields.ArrayField(base_field=models.CharField(max_length=255), blank=True, size=None, default=list)),
                ('_enrolled_student_names', django.contrib.postgres.fields.ArrayField(base_field=models.CharField(max_length=255), blank=True, size=None, default=list)),
                ('course', models.ForeignKey(to='autograder.Course', related_name='semesters')),
            ],
            bases=('autograder.modelvalidatableonsave',),
        ),
        migrations.CreateModel(
            name='Submission',
            fields=[
                ('modelvalidatableonsave_ptr', models.OneToOneField(parent_link=True, auto_created=True, serialize=False, primary_key=True, to='autograder.ModelValidatableOnSave')),
                ('ignore_extra_files', models.BooleanField(default=True)),
                ('_timestamp', models.DateTimeField(auto_now_add=True)),
            ],
            bases=('autograder.modelvalidatableonsave',),
        ),
        migrations.CreateModel(
            name='SubmissionGroup',
            fields=[
                ('modelvalidatableonsave_ptr', models.OneToOneField(parent_link=True, auto_created=True, serialize=False, primary_key=True, to='autograder.ModelValidatableOnSave')),
                ('extended_due_date', models.DateTimeField(null=True, blank=True, default=None)),
                ('members', models.ManyToManyField(to=settings.AUTH_USER_MODEL, related_name='submission_groups')),
                ('project', models.ForeignKey(to='autograder.Project')),
            ],
            bases=('autograder.modelvalidatableonsave',),
        ),
        migrations.AddField(
            model_name='autogradertestcaseresultbase',
            name='polymorphic_ctype',
            field=models.ForeignKey(to='contenttypes.ContentType', editable=False, null=True, related_name='polymorphic_autograder.autogradertestcaseresultbase_set+'),
        ),
        migrations.AddField(
            model_name='autogradertestcaseresultbase',
            name='test_case',
            field=models.ForeignKey(to='autograder.AutograderTestCaseBase'),
        ),
        migrations.AddField(
            model_name='autogradertestcasebase',
            name='polymorphic_ctype',
            field=models.ForeignKey(to='contenttypes.ContentType', editable=False, null=True, related_name='polymorphic_autograder.autogradertestcasebase_set+'),
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
