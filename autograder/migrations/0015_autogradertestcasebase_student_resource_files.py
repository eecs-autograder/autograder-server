# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations
import django.contrib.postgres.fields


class Migration(migrations.Migration):

    dependencies = [
        ('autograder', '0014_submission_show_all_test_cases'),
    ]

    operations = [
        migrations.AddField(
            model_name='autogradertestcasebase',
            name='student_resource_files',
            field=django.contrib.postgres.fields.ArrayField(default=list, blank=True, base_field=models.CharField(max_length=255), size=None),
        ),
    ]
