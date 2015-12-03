# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations
import autograder.models.fields


class Migration(migrations.Migration):

    dependencies = [
        ('autograder', '0031_auto_20151202_2339'),
    ]

    operations = [
        migrations.AlterField(
            model_name='studenttestsuitebase',
            name='compiler_flags',
            field=autograder.models.fields.StringListField(size=None, base_field=models.CharField(blank=True, max_length=255), default=list, blank=True),
        ),
        migrations.AlterField(
            model_name='studenttestsuitebase',
            name='suite_resource_files_to_compile_together',
            field=autograder.models.fields.StringListField(size=None, base_field=models.CharField(blank=True, max_length=255), default=list, blank=True),
        ),
    ]
