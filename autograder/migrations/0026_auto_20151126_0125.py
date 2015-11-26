# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations
import picklefield.fields
import django.core.validators
import django.contrib.postgres.fields


class Migration(migrations.Migration):

    dependencies = [
        ('autograder', '0025_compiledstudenttestsuite'),
    ]

    operations = [
        migrations.AddField(
            model_name='studenttestsuitebase',
            name='buggy_implementation_filenames',
            field=django.contrib.postgres.fields.ArrayField(base_field=models.CharField(max_length=255, blank=True), default=list, blank=True, size=None),
        ),
        migrations.AddField(
            model_name='studenttestsuitebase',
            name='correct_implementation_filename',
            field=models.CharField(default='', max_length=255),
            preserve_default=False,
        ),
        migrations.AddField(
            model_name='studenttestsuitebase',
            name='hide_from_students',
            field=models.BooleanField(default=True),
        ),
        migrations.AddField(
            model_name='studenttestsuitebase',
            name='implementation_file_alias',
            field=models.CharField(default='', max_length=255),
            preserve_default=False,
        ),
        migrations.AddField(
            model_name='studenttestsuitebase',
            name='name',
            field=models.CharField(default='', max_length=255),
            preserve_default=False,
        ),
        migrations.AddField(
            model_name='studenttestsuitebase',
            name='project',
            field=models.ForeignKey(default=None, to='autograder.Project', related_name='student_test_suites'),
        ),
        migrations.AddField(
            model_name='studenttestsuitebase',
            name='student_test_case_filename_pattern',
            field=picklefield.fields.PickledObjectField(editable=False, default=''),
            preserve_default=False,
        ),
        migrations.AddField(
            model_name='studenttestsuitebase',
            name='suite_resource_filenames',
            field=django.contrib.postgres.fields.ArrayField(base_field=models.CharField(max_length=255, blank=True), default=list, blank=True, size=None),
        ),
        migrations.AddField(
            model_name='studenttestsuitebase',
            name='time_limit',
            field=models.IntegerField(default=10, validators=[django.core.validators.MinValueValidator(1), django.core.validators.MaxValueValidator(60)]),
        ),
        migrations.AlterUniqueTogether(
            name='studenttestsuitebase',
            unique_together=set([('name', 'project')]),
        ),
    ]
