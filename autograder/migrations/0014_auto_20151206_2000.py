# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
        ('autograder', '0013_auto_20151206_0733'),
    ]

    operations = [
        migrations.RenameField(
            model_name='submission',
            old_name='show_all_test_cases',
            new_name='show_all_test_cases_and_suites',
        ),
    ]
