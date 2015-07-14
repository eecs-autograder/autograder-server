# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations
import django.contrib.postgres.fields


class Migration(migrations.Migration):

    dependencies = [
        ('autograder', '0002_auto_20150714_1753'),
    ]

    operations = [
        migrations.AlterField(
            model_name='project',
            name='required_student_files',
            field=django.contrib.postgres.fields.ArrayField(base_field=models.CharField(max_length=255), blank=True, size=None, default=[]),
        ),
    ]
