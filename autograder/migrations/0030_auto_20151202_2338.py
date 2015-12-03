# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations
import django.contrib.postgres.fields


class Migration(migrations.Migration):

    dependencies = [
        ('autograder', '0029_auto_20151126_0154'),
    ]

    operations = [
        migrations.AddField(
            model_name='studenttestsuitebase',
            name='compiler',
            field=models.CharField(default='g++', max_length=255),
            preserve_default=False,
        ),
        migrations.AddField(
            model_name='studenttestsuitebase',
            name='compiler_flags',
            field=django.contrib.postgres.fields.ArrayField(default=list, base_field=models.CharField(blank=True, max_length=255), blank=True, size=None),
        ),
        migrations.AddField(
            model_name='studenttestsuitebase',
            name='suite_resource_files_to_compile_together',
            field=django.contrib.postgres.fields.ArrayField(default=list, base_field=models.CharField(blank=True, max_length=255), blank=True, size=None),
        ),
    ]
