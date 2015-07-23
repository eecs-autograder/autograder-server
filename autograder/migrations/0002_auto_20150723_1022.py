# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations
import django.contrib.postgres.fields


class Migration(migrations.Migration):

    dependencies = [
        ('autograder', '0001_initial'),
    ]

    operations = [
        migrations.AddField(
            model_name='semester',
            name='_enrolled_students',
            field=django.contrib.postgres.fields.ArrayField(blank=True, default=list, base_field=models.CharField(max_length=255), size=None),
        ),
        migrations.AddField(
            model_name='semester',
            name='_semester_staff',
            field=django.contrib.postgres.fields.ArrayField(blank=True, default=list, base_field=models.CharField(max_length=255), size=None),
        ),
    ]
