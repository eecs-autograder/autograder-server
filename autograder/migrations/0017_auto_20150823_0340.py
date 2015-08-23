# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations
import django.contrib.postgres.fields


class Migration(migrations.Migration):

    dependencies = [
        ('autograder', '0016_auto_20150823_0107'),
    ]

    operations = [
        migrations.AlterField(
            model_name='submissiongroup',
            name='_members',
            field=django.contrib.postgres.fields.ArrayField(base_field=models.CharField(max_length=30), db_column='members', size=None),
        ),
    ]
