# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
        ('autograder', '0024_auto_20151206_2222'),
    ]

    operations = [
        migrations.RenameField(
            model_name='autogradertestcasebase',
            old_name='points_for_no_valgrind_errors',
            new_name='deduction_for_valgrind_errors',
        ),
    ]
