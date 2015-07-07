# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations
import autograder.models.autograder_test_case
import django.contrib.postgres.fields


class Migration(migrations.Migration):

    dependencies = [
        ('autograder', '0001_initial'),
    ]

    operations = [
        migrations.CreateModel(
            name='AutograderTestCaseBase',
            fields=[
                ('modelvalidatableonsave_ptr', models.OneToOneField(auto_created=True, primary_key=True, serialize=False, parent_link=True, to='autograder.ModelValidatableOnSave')),
                ('name', models.CharField(max_length=255)),
                ('command_line_arguments', django.contrib.postgres.fields.ArrayField(base_field=models.CharField(max_length=255, validators=[autograder.models.autograder_test_case._validate_cmd_line_arg]), size=None, default=[])),
                ('standard_input', models.TextField()),
                ('test_resource_files', django.contrib.postgres.fields.ArrayField(base_field=models.CharField(max_length=255), size=None, default=[])),
                ('time_limit', models.IntegerField(default=10)),
                ('expected_return_code', models.IntegerField(default=None, null=True)),
                ('expect_any_nonzero_return_code', models.BooleanField(default=False)),
                ('expected_standard_output', models.TextField()),
                ('expected_standard_error_output', models.TextField()),
                ('_use_valgrind', models.BooleanField(default=False)),
                ('valgrind_flags', django.contrib.postgres.fields.ArrayField(base_field=models.CharField(max_length=255, validators=[autograder.models.autograder_test_case._validate_cmd_line_arg]), size=None, default=None, null=True)),
                ('compiler', models.CharField(max_length=255)),
                ('compiler_flags', django.contrib.postgres.fields.ArrayField(base_field=models.CharField(max_length=255, validators=[autograder.models.autograder_test_case._validate_cmd_line_arg]), size=None, default=[])),
                ('files_to_compile_together', django.contrib.postgres.fields.ArrayField(base_field=models.CharField(max_length=255), size=None, default=[])),
                ('executable_name', models.CharField(max_length=255)),
            ],
            bases=('autograder.modelvalidatableonsave',),
        ),
        migrations.CreateModel(
            name='AutograderTestCaseResultBase',
            fields=[
                ('id', models.AutoField(verbose_name='ID', primary_key=True, auto_created=True, serialize=False)),
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
        ),
        migrations.CreateModel(
            name='CompiledAutograderTestCase',
            fields=[
                ('autogradertestcasebase_ptr', models.OneToOneField(auto_created=True, primary_key=True, serialize=False, parent_link=True, to='autograder.AutograderTestCaseBase')),
            ],
            bases=('autograder.autogradertestcasebase',),
        ),
        migrations.CreateModel(
            name='CompiledAutograderTestCaseResult',
            fields=[
                ('autogradertestcaseresultbase_ptr', models.OneToOneField(auto_created=True, primary_key=True, serialize=False, parent_link=True, to='autograder.AutograderTestCaseResultBase')),
            ],
            bases=('autograder.autogradertestcaseresultbase',),
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
        migrations.AlterUniqueTogether(
            name='autogradertestcasebase',
            unique_together=set([('name', 'project')]),
        ),
    ]
