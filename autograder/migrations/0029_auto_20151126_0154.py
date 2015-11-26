# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
        ('autograder', '0028_auto_20151126_0135'),
    ]

    operations = [
        migrations.AlterField(
            model_name='studenttestsuitebase',
            name='student_test_case_filename_pattern',
            field=models.CharField(max_length=255),
        ),
    ]
