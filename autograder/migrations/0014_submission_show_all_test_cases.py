# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
        ('autograder', '0013_auto_20150815_1456'),
    ]

    operations = [
        migrations.AddField(
            model_name='submission',
            name='show_all_test_cases',
            field=models.BooleanField(default=False),
        ),
    ]
