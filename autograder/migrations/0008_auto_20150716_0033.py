# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations
import django.contrib.postgres.fields


class Migration(migrations.Migration):

    dependencies = [
        ('autograder', '0007_auto_20150715_2356'),
    ]

    operations = [
        migrations.AlterField(
            model_name='autogradertestcasebase',
            name='compiler_flags',
            field=django.contrib.postgres.fields.ArrayField(size=None, default=[], blank=True, base_field=models.CharField(blank=True, max_length=255)),
        ),
        migrations.AlterField(
            model_name='autogradertestcasebase',
            name='executable_name',
            field=models.CharField(blank=True, max_length=255),
        ),
    ]
