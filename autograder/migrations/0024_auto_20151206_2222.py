# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations
import django.contrib.postgres.fields
import re
import autograder.models.feedback_configuration
import autograder.models.fields
import django.core.validators


class Migration(migrations.Migration):

    dependencies = [
        ('autograder', '0023_auto_20150914_2113'),
    ]

    operations = [
        migrations.CreateModel(
            name='StudentTestSuiteBase',
            fields=[
                ('polymorphicmodelvalidatableonsave_ptr', models.OneToOneField(to='autograder.PolymorphicModelValidatableOnSave', auto_created=True, serialize=False, primary_key=True, parent_link=True)),
                ('name', models.CharField(max_length=255)),
                ('student_test_case_filename_pattern', models.CharField(max_length=255)),
                ('correct_implementation_filename', models.CharField(max_length=255)),
                ('buggy_implementation_filenames', django.contrib.postgres.fields.ArrayField(size=None, blank=True, default=list, base_field=models.CharField(max_length=255, blank=True))),
                ('implementation_file_alias', models.CharField(max_length=255, blank=True)),
                ('suite_resource_filenames', django.contrib.postgres.fields.ArrayField(size=None, blank=True, default=list, base_field=models.CharField(max_length=255, blank=True))),
                ('time_limit', models.IntegerField(validators=[django.core.validators.MinValueValidator(1), django.core.validators.MaxValueValidator(60)], default=10)),
                ('hide_from_students', models.BooleanField(default=True)),
                ('points_per_buggy_implementation_exposed', models.IntegerField(validators=[django.core.validators.MinValueValidator(0)], default=0)),
                ('compiler', models.CharField(choices=[('g++', 'g++')], max_length=255, default='g++')),
                ('compiler_flags', autograder.models.fields.StringListField(size=None, blank=True, allow_empty_strings=False, string_validators=[django.core.validators.RegexValidator(re.compile('^[a-zA-Z0-9-_=.]+$', 32))], strip_strings=True, default=list)),
                ('suite_resource_files_to_compile_together', autograder.models.fields.StringListField(size=None, blank=True, allow_empty_strings=False, string_validators=[], strip_strings=True, default=list)),
                ('compile_implementation_files', models.BooleanField(default=True)),
            ],
            bases=('autograder.polymorphicmodelvalidatableonsave',),
        ),
        migrations.CreateModel(
            name='StudentTestSuiteResult',
            fields=[
                ('id', models.AutoField(primary_key=True, auto_created=True, verbose_name='ID', serialize=False)),
                ('buggy_implementations_exposed', autograder.models.fields.ClassField(class_=set, editable=False, default=set)),
                ('detailed_results', autograder.models.fields.ClassField(blank=True, editable=False, class_=list, default=list)),
            ],
        ),
        migrations.RenameField(
            model_name='submission',
            old_name='show_all_test_cases',
            new_name='show_all_test_cases_and_suites',
        ),
        migrations.AddField(
            model_name='project',
            name='student_test_suite_feedback_configuration',
            field=autograder.models.fields.ClassField(class_=autograder.models.feedback_configuration.StudentTestSuiteFeedbackConfiguration, editable=False, default=autograder.models.feedback_configuration.StudentTestSuiteFeedbackConfiguration),
        ),
        migrations.AddField(
            model_name='submission',
            name='student_test_suite_feedback_config_override',
            field=autograder.models.fields.ClassField(class_=autograder.models.feedback_configuration.StudentTestSuiteFeedbackConfiguration, editable=False, default=None, null=True),
        ),
        migrations.CreateModel(
            name='CompiledStudentTestSuite',
            fields=[
                ('studenttestsuitebase_ptr', models.OneToOneField(to='autograder.StudentTestSuiteBase', auto_created=True, serialize=False, primary_key=True, parent_link=True)),
            ],
            options={
                'abstract': False,
            },
            bases=('autograder.studenttestsuitebase',),
        ),
        migrations.AddField(
            model_name='studenttestsuiteresult',
            name='submission',
            field=models.ForeignKey(blank=True, to='autograder.Submission', null=True, related_name='suite_results', default=None),
        ),
        migrations.AddField(
            model_name='studenttestsuiteresult',
            name='test_suite',
            field=models.ForeignKey(to='autograder.StudentTestSuiteBase'),
        ),
        migrations.AddField(
            model_name='studenttestsuitebase',
            name='project',
            field=models.ForeignKey(to='autograder.Project', related_name='student_test_suites'),
        ),
        migrations.AlterUniqueTogether(
            name='studenttestsuitebase',
            unique_together=set([('name', 'project')]),
        ),
    ]
