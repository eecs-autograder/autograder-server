# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations
import django.contrib.postgres.fields


class Migration(migrations.Migration):

    dependencies = [
        ('autograder', '0008_auto_20150809_2010'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='submissiongroup',
            name='members',
        ),
        migrations.AddField(
            model_name='submissiongroup',
            name='members',
            field=django.contrib.postgres.fields.ArrayField(default=[], base_field=models.CharField(max_length=30), size=None),
            preserve_default=False,
        ),
    ]
