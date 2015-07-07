# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations
import autograder.models.project
import autograder.models.autograder_test_case
import django.contrib.postgres.fields
import autograder.shared.utilities


class Migration(migrations.Migration):

    dependencies = [
        ('autograder', '0002_auto_20150706_1110'),
    ]

    operations = [
        migrations.AlterUniqueTogether(
            name='_requiredstudentfile',
            unique_together=set([]),
        ),
        migrations.RemoveField(
            model_name='_requiredstudentfile',
            name='modelvalidatableonsave_ptr',
        ),
        migrations.RemoveField(
            model_name='_requiredstudentfile',
            name='project',
        ),
        migrations.RemoveField(
            model_name='_uploadedprojectfile',
            name='modelvalidatableonsave_ptr',
        ),
        migrations.RemoveField(
            model_name='_uploadedprojectfile',
            name='project',
        ),
        migrations.AddField(
            model_name='project',
            name='project_files',
            field=django.contrib.postgres.fields.ArrayField(base_field=models.FileField(upload_to=autograder.models.project._get_project_file_upload_to_dir, validators=[autograder.models.project._validate_filename]), size=None, default=[]),
        ),
        migrations.AddField(
            model_name='project',
            name='required_student_files',
            field=django.contrib.postgres.fields.ArrayField(base_field=models.CharField(max_length=255, validators=[autograder.shared.utilities.check_user_provided_filename]), size=None, default=[]),
        ),
        migrations.AlterField(
            model_name='autogradertestcasebase',
            name='command_line_arguments',
            field=django.contrib.postgres.fields.ArrayField(base_field=models.CharField(max_length=255, validators=[autograder.models.autograder_test_case._validate_cmd_line_arg]), size=None, default=[], blank=True),
        ),
        migrations.AlterField(
            model_name='autogradertestcasebase',
            name='compiler',
            field=models.CharField(max_length=255, blank=True),
        ),
        migrations.AlterField(
            model_name='autogradertestcasebase',
            name='compiler_flags',
            field=django.contrib.postgres.fields.ArrayField(base_field=models.CharField(max_length=255, validators=[autograder.models.autograder_test_case._validate_cmd_line_arg]), size=None, default=[], blank=True),
        ),
        migrations.AlterField(
            model_name='autogradertestcasebase',
            name='executable_name',
            field=models.CharField(max_length=255, blank=True),
        ),
        migrations.AlterField(
            model_name='autogradertestcasebase',
            name='expected_return_code',
            field=models.IntegerField(default=None, blank=True, null=True),
        ),
        migrations.AlterField(
            model_name='autogradertestcasebase',
            name='expected_standard_error_output',
            field=models.TextField(blank=True),
        ),
        migrations.AlterField(
            model_name='autogradertestcasebase',
            name='expected_standard_output',
            field=models.TextField(blank=True),
        ),
        migrations.AlterField(
            model_name='autogradertestcasebase',
            name='files_to_compile_together',
            field=django.contrib.postgres.fields.ArrayField(base_field=models.CharField(max_length=255), size=None, default=[], blank=True),
        ),
        migrations.AlterField(
            model_name='autogradertestcasebase',
            name='standard_input',
            field=models.TextField(blank=True),
        ),
        migrations.AlterField(
            model_name='autogradertestcasebase',
            name='test_resource_files',
            field=django.contrib.postgres.fields.ArrayField(base_field=models.CharField(max_length=255), size=None, default=[], blank=True),
        ),
        migrations.AlterField(
            model_name='autogradertestcasebase',
            name='valgrind_flags',
            field=django.contrib.postgres.fields.ArrayField(base_field=models.CharField(max_length=255, validators=[autograder.models.autograder_test_case._validate_cmd_line_arg]), size=None, default=None, blank=True, null=True),
        ),
        migrations.DeleteModel(
            name='_RequiredStudentFile',
        ),
        migrations.DeleteModel(
            name='_UploadedProjectFile',
        ),
    ]
