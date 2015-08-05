# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
        ('autograder', '0004_submission_ignore_extra_files'),
    ]

    operations = [
        migrations.AddField(
            model_name='project',
            name='allow_submissions_from_non_enrolled_students',
            field=models.BooleanField(default=False),
        ),
    ]
