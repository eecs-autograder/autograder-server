# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
        ('autograder', '0002_auto_20150804_1413'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='submission',
            name='ignore_extra_files',
        ),
        migrations.AddField(
            model_name='autogradertestcasebase',
            name='hide_from_students',
            field=models.BooleanField(default=True),
        ),
    ]
