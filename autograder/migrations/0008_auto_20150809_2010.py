# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations
import django.contrib.postgres.fields


class Migration(migrations.Migration):

    dependencies = [
        ('autograder', '0007_auto_20150809_2007'),
    ]

    operations = [
        migrations.AlterField(
            model_name='submission',
            name='discarded_files',
            field=django.contrib.postgres.fields.ArrayField(size=None, default=list, base_field=models.CharField(max_length=255), blank=True),
        ),
    ]
