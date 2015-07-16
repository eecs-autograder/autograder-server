# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations
import django.contrib.postgres.fields
import django.core.validators


class Migration(migrations.Migration):

    dependencies = [
        ('autograder', '0006_auto_20150714_2218'),
    ]

    operations = [
        migrations.AlterField(
            model_name='autogradertestcasebase',
            name='command_line_arguments',
            field=django.contrib.postgres.fields.ArrayField(size=None, blank=True, base_field=models.CharField(blank=True, max_length=255), default=[]),
        ),
        migrations.AlterField(
            model_name='autogradertestcasebase',
            name='time_limit',
            field=models.IntegerField(default=10, validators=[django.core.validators.MinValueValidator(1)]),
        ),
        migrations.AlterField(
            model_name='autogradertestcasebase',
            name='valgrind_flags',
            field=django.contrib.postgres.fields.ArrayField(size=None, blank=True, base_field=models.CharField(blank=True, max_length=255), null=True, default=None),
        ),
    ]
