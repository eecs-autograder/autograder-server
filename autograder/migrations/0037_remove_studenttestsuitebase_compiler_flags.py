# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
        ('autograder', '0036_auto_20151203_0121'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='studenttestsuitebase',
            name='compiler_flags',
        ),
    ]
