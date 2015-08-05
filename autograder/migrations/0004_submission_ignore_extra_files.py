# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
        ('autograder', '0003_auto_20150805_1359'),
    ]

    operations = [
        migrations.AddField(
            model_name='submission',
            name='ignore_extra_files',
            field=models.BooleanField(default=True),
        ),
    ]
