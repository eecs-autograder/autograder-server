# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations
import autograder.shared.utilities
import autograder.models.project
import django.core.validators
import django.contrib.postgres.fields
import autograder.models.autograder_test_case
from django.conf import settings


class Migration(migrations.Migration):

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name='AutograderTestCaseResultBase',
            fields=[
                ('id', models.AutoField(primary_key=True, verbose_name='ID', serialize=False, auto_created=True)),
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
                ('id', models.AutoField(primary_key=True, verbose_name='ID', serialize=False, auto_created=True)),
            ],
        ),
        migrations.CreateModel(
            name='_ExpectedStudentFilePattern',
            fields=[
                ('modelvalidatableonsave_ptr', models.OneToOneField(primary_key=True, serialize=False, parent_link=True, auto_created=True, to='autograder.ModelValidatableOnSave')),
                ('pattern', models.CharField(validators=[autograder.shared.utilities.check_shell_style_file_pattern], max_length=255)),
                ('min_num_matches', models.IntegerField(validators=[django.core.validators.MinValueValidator(0)])),
                ('max_num_matches', models.IntegerField(validators=[django.core.validators.MinValueValidator(0)])),
            ],
            bases=('autograder.modelvalidatableonsave',),
        ),
        migrations.CreateModel(
            name='_RequiredStudentFile',
            fields=[
                ('modelvalidatableonsave_ptr', models.OneToOneField(primary_key=True, serialize=False, parent_link=True, auto_created=True, to='autograder.ModelValidatableOnSave')),
                ('filename', models.CharField(validators=[autograder.shared.utilities.check_user_provided_filename], max_length=255)),
            ],
            bases=('autograder.modelvalidatableonsave',),
        ),
        migrations.CreateModel(
            name='_UploadedProjectFile',
            fields=[
                ('modelvalidatableonsave_ptr', models.OneToOneField(primary_key=True, serialize=False, parent_link=True, auto_created=True, to='autograder.ModelValidatableOnSave')),
                ('uploaded_file', models.FileField(upload_to=autograder.models.project._get_project_file_upload_to_dir, validators=[autograder.models.project._validate_filename])),
            ],
            bases=('autograder.modelvalidatableonsave',),
        ),
        migrations.CreateModel(
            name='AutograderTestCaseBase',
            fields=[
                ('modelvalidatableonsave_ptr', models.OneToOneField(primary_key=True, serialize=False, parent_link=True, auto_created=True, to='autograder.ModelValidatableOnSave')),
                ('name', models.CharField(max_length=255)),
                ('command_line_arguments', django.contrib.postgres.fields.ArrayField(blank=True, size=None, default=[], base_field=models.CharField(validators=[autograder.models.autograder_test_case._validate_cmd_line_arg], max_length=255))),
                ('standard_input', models.TextField(blank=True)),
                ('test_resource_files', django.contrib.postgres.fields.ArrayField(blank=True, size=None, default=[], base_field=models.CharField(max_length=255))),
                ('time_limit', models.IntegerField(default=10)),
                ('expected_return_code', models.IntegerField(null=True, blank=True, default=None)),
                ('expect_any_nonzero_return_code', models.BooleanField(default=False)),
                ('expected_standard_output', models.TextField(blank=True)),
                ('expected_standard_error_output', models.TextField(blank=True)),
                ('_use_valgrind', models.BooleanField(default=False)),
                ('valgrind_flags', django.contrib.postgres.fields.ArrayField(null=True, blank=True, size=None, default=None, base_field=models.CharField(validators=[autograder.models.autograder_test_case._validate_cmd_line_arg], max_length=255))),
                ('compiler', models.CharField(blank=True, max_length=255)),
                ('compiler_flags', django.contrib.postgres.fields.ArrayField(blank=True, size=None, default=[], base_field=models.CharField(validators=[autograder.models.autograder_test_case._validate_cmd_line_arg], max_length=255))),
                ('files_to_compile_together', django.contrib.postgres.fields.ArrayField(blank=True, size=None, default=[], base_field=models.CharField(max_length=255))),
                ('executable_name', models.CharField(validators=[autograder.shared.utilities.check_user_provided_filename], blank=True, max_length=255)),
            ],
            bases=('autograder.modelvalidatableonsave',),
        ),
        migrations.CreateModel(
            name='CompiledAutograderTestCaseResult',
            fields=[
                ('autogradertestcaseresultbase_ptr', models.OneToOneField(primary_key=True, serialize=False, parent_link=True, auto_created=True, to='autograder.AutograderTestCaseResultBase')),
            ],
            bases=('autograder.autogradertestcaseresultbase',),
        ),
        migrations.CreateModel(
            name='Course',
            fields=[
                ('modelvalidatableonsave_ptr', models.OneToOneField(parent_link=True, auto_created=True, to='autograder.ModelValidatableOnSave')),
                ('name', models.CharField(primary_key=True, serialize=False, max_length=255)),
            ],
            bases=('autograder.modelvalidatableonsave',),
        ),
        migrations.CreateModel(
            name='Project',
            fields=[
                ('modelvalidatableonsave_ptr', models.OneToOneField(primary_key=True, serialize=False, parent_link=True, auto_created=True, to='autograder.ModelValidatableOnSave')),
                ('name', models.CharField(max_length=255)),
                ('visible_to_students', models.BooleanField(default=False)),
                ('closing_time', models.DateTimeField(null=True, blank=True, default=None)),
                ('disallow_student_submissions', models.BooleanField(default=False)),
                ('min_group_size', models.IntegerField(validators=[django.core.validators.MinValueValidator(1)], default=1)),
                ('max_group_size', models.IntegerField(validators=[django.core.validators.MinValueValidator(1)], default=1)),
            ],
            bases=('autograder.modelvalidatableonsave',),
        ),
        migrations.CreateModel(
            name='Semester',
            fields=[
                ('modelvalidatableonsave_ptr', models.OneToOneField(primary_key=True, serialize=False, parent_link=True, auto_created=True, to='autograder.ModelValidatableOnSave')),
                ('name', models.CharField(max_length=255)),
                ('course', models.ForeignKey(to='autograder.Course')),
            ],
            bases=('autograder.modelvalidatableonsave',),
        ),
        migrations.CreateModel(
            name='Submission',
            fields=[
                ('modelvalidatableonsave_ptr', models.OneToOneField(primary_key=True, serialize=False, parent_link=True, auto_created=True, to='autograder.ModelValidatableOnSave')),
                ('_timestamp', models.DateTimeField(auto_now_add=True)),
            ],
            bases=('autograder.modelvalidatableonsave',),
        ),
        migrations.CreateModel(
            name='SubmissionGroup',
            fields=[
                ('modelvalidatableonsave_ptr', models.OneToOneField(primary_key=True, serialize=False, parent_link=True, auto_created=True, to='autograder.ModelValidatableOnSave')),
                ('extended_due_date', models.DateTimeField(null=True, blank=True, default=None)),
                ('members', models.ManyToManyField(to=settings.AUTH_USER_MODEL, related_name='submission_groups')),
                ('project', models.ForeignKey(to='autograder.Project')),
            ],
            bases=('autograder.modelvalidatableonsave',),
        ),
        migrations.CreateModel(
            name='CompiledAutograderTestCase',
            fields=[
                ('autogradertestcasebase_ptr', models.OneToOneField(primary_key=True, serialize=False, parent_link=True, auto_created=True, to='autograder.AutograderTestCaseBase')),
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
            field=models.ForeignKey(to='autograder.Project', related_name='project_files'),
        ),
        migrations.AddField(
            model_name='_requiredstudentfile',
            name='project',
            field=models.ForeignKey(to='autograder.Project', related_name='required_student_files'),
        ),
        migrations.AddField(
            model_name='_expectedstudentfilepattern',
            name='project',
            field=models.ForeignKey(to='autograder.Project', related_name='expected_student_file_patterns'),
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
