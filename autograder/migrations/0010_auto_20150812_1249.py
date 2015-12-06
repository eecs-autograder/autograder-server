# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
        ('autograder', '0009_auto_20150812_1149'),
    ]

    operations = [
        migrations.RenameField(
            model_name='submissiongroup',
            old_name='members',
            new_name='_members',
        ),
    ]
