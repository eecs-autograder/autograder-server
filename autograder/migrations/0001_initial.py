# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations
import autograder.models.project
import autograder.models.autograder_test_case
from django.conf import settings
import django.core.validators
import autograder.shared.utilities
import autograder.models.submission
import django.contrib.postgres.fields


class Migration(migrations.Migration):

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name='AutograderTestCaseResultBase',
            fields=[
                ('id', models.AutoField(serialize=False, verbose_name='ID', primary_key=True, auto_created=True)),
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
        ),
        migrations.CreateModel(
            name='ModelValidatableOnSave',
            fields=[
                ('id', models.AutoField(serialize=False, verbose_name='ID', primary_key=True, auto_created=True)),
            ],
        ),
        migrations.CreateModel(
            name='_ExpectedStudentFilePattern',
            fields=[
                ('modelvalidatableonsave_ptr', models.OneToOneField(parent_link=True, to='autograder.ModelValidatableOnSave', serialize=False, primary_key=True, auto_created=True)),
                ('pattern', models.CharField(max_length=255, validators=[autograder.shared.utilities.check_shell_style_file_pattern])),
                ('min_num_matches', models.IntegerField(validators=[django.core.validators.MinValueValidator(0)])),
                ('max_num_matches', models.IntegerField(validators=[django.core.validators.MinValueValidator(0)])),
            ],
            bases=('autograder.modelvalidatableonsave',),
        ),
        migrations.CreateModel(
            name='_RequiredStudentFile',
            fields=[
                ('modelvalidatableonsave_ptr', models.OneToOneField(parent_link=True, to='autograder.ModelValidatableOnSave', serialize=False, primary_key=True, auto_created=True)),
                ('filename', models.CharField(max_length=255, validators=[autograder.shared.utilities.check_user_provided_filename])),
            ],
            bases=('autograder.modelvalidatableonsave',),
        ),
        migrations.CreateModel(
            name='_UploadedProjectFile',
            fields=[
                ('modelvalidatableonsave_ptr', models.OneToOneField(parent_link=True, to='autograder.ModelValidatableOnSave', serialize=False, primary_key=True, auto_created=True)),
                ('uploaded_file', models.FileField(upload_to=autograder.models.project._get_project_file_upload_to_dir, validators=[autograder.models.project._validate_filename])),
            ],
            bases=('autograder.modelvalidatableonsave',),
        ),
        migrations.CreateModel(
            name='AutograderTestCaseBase',
            fields=[
                ('modelvalidatableonsave_ptr', models.OneToOneField(parent_link=True, to='autograder.ModelValidatableOnSave', serialize=False, primary_key=True, auto_created=True)),
                ('name', models.CharField(max_length=255)),
                ('command_line_arguments', django.contrib.postgres.fields.ArrayField(blank=True, base_field=models.CharField(max_length=255, validators=[autograder.models.autograder_test_case._validate_cmd_line_arg]), default=[], size=None)),
                ('standard_input', models.TextField(blank=True)),
                ('test_resource_files', django.contrib.postgres.fields.ArrayField(blank=True, base_field=models.CharField(max_length=255), default=[], size=None)),
                ('time_limit', models.IntegerField(default=10)),
                ('expected_return_code', models.IntegerField(blank=True, null=True, default=None)),
                ('expect_any_nonzero_return_code', models.BooleanField(default=False)),
                ('expected_standard_output', models.TextField(blank=True)),
                ('expected_standard_error_output', models.TextField(blank=True)),
                ('_use_valgrind', models.BooleanField(default=False)),
                ('valgrind_flags', django.contrib.postgres.fields.ArrayField(blank=True, null=True, base_field=models.CharField(max_length=255, validators=[autograder.models.autograder_test_case._validate_cmd_line_arg]), default=None, size=None)),
                ('compiler', models.CharField(max_length=255, blank=True)),
                ('compiler_flags', django.contrib.postgres.fields.ArrayField(blank=True, base_field=models.CharField(max_length=255, validators=[autograder.models.autograder_test_case._validate_cmd_line_arg]), default=[], size=None)),
                ('files_to_compile_together', django.contrib.postgres.fields.ArrayField(blank=True, base_field=models.CharField(max_length=255), default=[], size=None)),
                ('executable_name', models.CharField(max_length=255, blank=True, validators=[autograder.shared.utilities.check_user_provided_filename])),
            ],
            bases=('autograder.modelvalidatableonsave',),
        ),
        migrations.CreateModel(
            name='CompiledAutograderTestCaseResult',
            fields=[
                ('autogradertestcaseresultbase_ptr', models.OneToOneField(parent_link=True, to='autograder.AutograderTestCaseResultBase', serialize=False, primary_key=True, auto_created=True)),
            ],
            bases=('autograder.autogradertestcaseresultbase',),
        ),
        migrations.CreateModel(
            name='Course',
            fields=[
                ('modelvalidatableonsave_ptr', models.OneToOneField(parent_link=True, to='autograder.ModelValidatableOnSave', auto_created=True)),
                ('name', models.CharField(max_length=255, serialize=False, primary_key=True)),
            ],
            bases=('autograder.modelvalidatableonsave',),
        ),
        migrations.CreateModel(
            name='Project',
            fields=[
                ('modelvalidatableonsave_ptr', models.OneToOneField(parent_link=True, to='autograder.ModelValidatableOnSave', serialize=False, primary_key=True, auto_created=True)),
                ('name', models.CharField(max_length=255)),
                ('visible_to_students', models.BooleanField(default=False)),
                ('closing_time', models.DateTimeField(blank=True, null=True, default=None)),
                ('disallow_student_submissions', models.BooleanField(default=False)),
                ('min_group_size', models.IntegerField(default=1, validators=[django.core.validators.MinValueValidator(1)])),
                ('max_group_size', models.IntegerField(default=1, validators=[django.core.validators.MinValueValidator(1)])),
            ],
            bases=('autograder.modelvalidatableonsave',),
        ),
        migrations.CreateModel(
            name='Semester',
            fields=[
                ('modelvalidatableonsave_ptr', models.OneToOneField(parent_link=True, to='autograder.ModelValidatableOnSave', serialize=False, primary_key=True, auto_created=True)),
                ('name', models.CharField(max_length=255)),
                ('course', models.ForeignKey(to='autograder.Course')),
            ],
            bases=('autograder.modelvalidatableonsave',),
        ),
        migrations.CreateModel(
            name='Submission',
            fields=[
                ('modelvalidatableonsave_ptr', models.OneToOneField(parent_link=True, to='autograder.ModelValidatableOnSave', serialize=False, primary_key=True, auto_created=True)),
                ('submitted_files', django.contrib.postgres.fields.ArrayField(size=None, base_field=models.FileField(upload_to=autograder.models.submission._get_submission_file_upload_to_dir, validators=[autograder.models.submission._validate_filename]))),
                ('_timestamp', models.DateTimeField(auto_now_add=True)),
            ],
            bases=('autograder.modelvalidatableonsave',),
        ),
        migrations.CreateModel(
            name='SubmissionGroup',
            fields=[
                ('modelvalidatableonsave_ptr', models.OneToOneField(parent_link=True, to='autograder.ModelValidatableOnSave', serialize=False, primary_key=True, auto_created=True)),
                ('extended_due_date', models.DateTimeField(blank=True, null=True, default=None)),
                ('members', models.ManyToManyField(to=settings.AUTH_USER_MODEL, related_name='submission_groups')),
                ('project', models.ForeignKey(to='autograder.Project')),
            ],
            bases=('autograder.modelvalidatableonsave',),
        ),
        migrations.CreateModel(
            name='CompiledAutograderTestCase',
            fields=[
                ('autogradertestcasebase_ptr', models.OneToOneField(parent_link=True, to='autograder.AutograderTestCaseBase', serialize=False, primary_key=True, auto_created=True)),
            ],
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
            field=models.ForeignKey(to='autograder.Semester'),
        ),
        migrations.AddField(
            model_name='autogradertestcaseresultbase',
            name='test_case',
            field=models.ForeignKey(to='autograder.AutograderTestCaseBase'),
        ),
        migrations.AddField(
            model_name='autogradertestcasebase',
            name='project',
            field=models.ForeignKey(to='autograder.Project'),
        ),
        migrations.AddField(
            model_name='_uploadedprojectfile',
            name='project',
            field=models.ForeignKey(related_name='project_files', to='autograder.Project'),
        ),
        migrations.AddField(
            model_name='_requiredstudentfile',
            name='project',
            field=models.ForeignKey(related_name='required_student_files', to='autograder.Project'),
        ),
        migrations.AddField(
            model_name='_expectedstudentfilepattern',
            name='project',
            field=models.ForeignKey(related_name='expected_student_file_patterns', to='autograder.Project'),
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
        migrations.AlterUniqueTogether(
            name='_requiredstudentfile',
            unique_together=set([('project', 'filename')]),
        ),
        migrations.AlterUniqueTogether(
            name='_expectedstudentfilepattern',
            unique_together=set([('project', 'pattern')]),
        ),
    ]
